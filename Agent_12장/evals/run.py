"""회귀 평가 실행기: 골든 세트를 n번 돌려 채점하고 기록을 남긴다.

사용법(저장소 맨 위에서)
    python -m evals.run --suite summary --prompt summary_v1 --runs 5
    python -m evals.run --suite ask --runs 5
    python -m evals.run --suite all --prompt summary_v2 --model sim-b --runs 5 --tag v2-simb

결과
    evals/runs/<tag>/records.jsonl   시행(문항 x 반복) 하나가 한 줄인 구조화 기록
    evals/runs/<tag>/summary.json    기준별 통과율, 문항별 통과 수, 표준오차 등 요약
    evals/runs/<tag>/llm.log         평가 중의 LLM 호출 기록(운영 기록 llm.log와 같은 형식)

--backend sim(기본)은 evals/sim.py의 변동 모의 모델을 쓴다. API를 부르지 않는다.
--backend real은 실제 모델을 부른다. ANTHROPIC_API_KEY와 LLM_MODEL이 있어야 하며 비용이 든다.
  두 값은 셸 환경 변수나 저장소 맨 위의 .env에서 읽는다(이미 셸에 있는 값이 앞선다).
  학생 각자의 키로 하는 실제 평가는 한 번만 한다: --backend real --runs 1 (12장 11-9, 편성표 §3).
"""

import argparse
import json
import logging
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# api를 불러오기 전에 환경을 정한다. 평가는 어느 컴퓨터에서나 같은 검색 결과를 얻도록 대체 임베딩을 쓴다.
# .env나 셸에 EMBED_BACKEND=auto가 있어도 평가에서는 대체 임베딩으로 고정한다(판본 비교의 조건 통제, 6-1).
os.environ["EMBED_BACKEND"] = "fallback"
os.environ.setdefault("RAG_INDEX_PATH", os.path.join(tempfile.gettempdir(), "jobprep-evals-index.json"))

EVALS_DIR = Path(__file__).resolve().parent
GOLDEN_DIR = EVALS_DIR / "golden"
RUNS_DIR = EVALS_DIR / "runs"
LOG_FORMAT = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S")


def load_env_file(path):
    """저장소의 .env를 읽어 셸에 없는 값만 환경 변수로 둔다(python-dotenv가 있으면 그것을 쓴다)."""
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=False)
        return
    except ImportError:
        pass
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_golden(suite):
    """골든 세트 파일(JSON Lines)을 읽어 문항 목록을 돌려준다."""
    path = GOLDEN_DIR / f"{suite}.jsonl"
    items = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise SystemExit(f"{path.name} {number}번째 줄을 읽지 못하였다: {error.msg}")
    return items


class TokenCounter(logging.Handler):
    """jobprep.llm 기록기의 줄에서 토큰 수와 오류를 모은다. 호출마다 reset()한다."""

    def __init__(self):
        super().__init__(logging.INFO)
        self.reset()

    def reset(self):
        self.calls, self.input_tokens, self.output_tokens, self.errors = 0, 0, 0, []

    def emit(self, record):
        fields = dict(part.split("=", 1) for part in record.getMessage().split() if "=" in part)
        if "input_tokens" in fields:
            self.calls += 1
            self.input_tokens += int(fields["input_tokens"])
            self.output_tokens += int(fields["output_tokens"])
        if "error" in fields:
            self.errors.append(fields["error"])


def evidence_for_ask(question):
    """질의응답 판정의 근거: 실행기와 같은 검색으로 고른 상위 청크의 글."""
    from rag.index import get_index
    from rag.search import search
    from api.ask import TOP_K
    return "\n".join(r["chunk"]["text"] for r in search(question, get_index(), top_k=TOP_K))


def run_once(suite, item):
    """문항 하나를 기능 함수에 넣어 (출력, 오류 이름)을 돌려준다."""
    from api import llm
    from api.summary import SummaryError, summarize
    from api.ask import answer_question
    try:
        if suite == "summary":
            return summarize(item["input"]), None
        return answer_question(item["question"]), None
    except SummaryError:
        return None, "SummaryError"
    except llm.LLMError as error:
        return None, f"LLMError: {error}"


def trial_passed(criteria, verdict):
    """시행 하나의 통과: 해당하는 규칙 기준이 모두 통과이고 판정이 pass이다."""
    rules_ok = all(ok for ok, _ in criteria.values() if ok is not None)
    return rules_ok and verdict == "pass"


def evaluate(suite, items, args, writer, counter):
    from api import llm
    from evals import graders, judge, sim

    trials = []
    for run in range(args.runs):
        if args.backend == "sim":
            llm.complete = sim.make_complete(args.model, run)
        for item in items:
            counter.reset()
            started = time.perf_counter()
            output, error = run_once(suite, item)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if suite == "ask" and output is None:
                criteria = {name: (False, "출력 없음") for name in graders.ASK_GRADERS}
            else:
                criteria = graders.grade(suite, item, output)
            evidence = item["input"] if suite == "summary" else evidence_for_ask(item["question"])
            verdict, reason = judge.judge(suite, evidence, output, backend=args.backend)
            record = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "run_id": args.tag, "suite": suite, "item": item["id"], "item_suite": item["suite"],
                "run": run, "backend": args.backend, "model": args.model,
                "prompt_version": llm.prompt_version(suite),
                "passed": trial_passed(criteria, verdict),
                "criteria": {k: v[0] for k, v in criteria.items()},
                "notes": {k: v[1] for k, v in criteria.items() if v[0] is False},
                "judge": verdict, "judge_reason": reason,
                "latency_ms": latency_ms, "llm_calls": counter.calls,
                "input_tokens": counter.input_tokens, "output_tokens": counter.output_tokens,
                "error": error or (counter.errors[0] if counter.errors else None),
            }
            writer.write(json.dumps(record, ensure_ascii=False) + "\n")
            trials.append(record)
    return trials


def rate(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def summarize_trials(items, trials, runs):
    """시행 기록을 기준별·문항별 통과율로 요약한다. 회귀 문항과 능력 문항을 나누어 센다."""
    per_item = {}
    for item in items:
        mine = [t for t in trials if t["item"] == item["id"]]
        per_item[item["id"]] = {"suite": item["suite"], "kind": item["kind"],
                                "passes": sum(t["passed"] for t in mine), "runs": runs}
    regression = [t for t in trials if t["item_suite"] == "regression"]
    names = list(trials[0]["criteria"]) if trials else []
    criteria = {name: rate([t["criteria"][name] for t in regression]) for name in names}
    criteria["judge"] = rate([t["judge"] == "pass" for t in regression])
    item_means = [v["passes"] / runs for v in per_item.values() if v["suite"] == "regression"]
    mean = statistics.fmean(item_means) if item_means else 0.0
    sem = statistics.stdev(item_means) / len(item_means) ** 0.5 if len(item_means) > 1 else 0.0
    capability = [t["passed"] for t in trials if t["item_suite"] == "capability"]
    per_run = [rate([t["passed"] for t in regression if t["run"] == r]) for r in range(runs)]
    return {
        "items": len(items),
        "regression_items": len(item_means),
        "trials": len(trials),
        "pass_rate": round(mean, 3),
        "sem": round(sem, 3),
        "ci95": [round(max(0.0, mean - 1.96 * sem), 3), round(min(1.0, mean + 1.96 * sem), 3)],
        "pass_all_runs": sum(1 for v in per_item.values() if v["suite"] == "regression" and v["passes"] == runs),
        "pass_any_run": sum(1 for v in per_item.values() if v["suite"] == "regression" and v["passes"] > 0),
        "per_run_pass_rate": per_run,
        "capability_pass_rate": rate(capability),
        "criteria": criteria,
        "per_item": per_item,
        "input_tokens": sum(t["input_tokens"] for t in trials),
        "output_tokens": sum(t["output_tokens"] for t in trials),
        "llm_calls": sum(t["llm_calls"] for t in trials),
        "mean_latency_ms": round(statistics.fmean(t["latency_ms"] for t in trials), 1) if trials else 0,
    }


def print_report(suite, result, args, prompt):
    print(f"[{suite}] 판본 {prompt} · 모델 {args.model} · 반복 {args.runs}회 · "
          f"문항 {result['items']}개(회귀 {result['regression_items']})")
    print("  기준별 통과율(회귀 문항)")
    for name, value in result["criteria"].items():
        shown = "해당 없음" if value is None else f"{value:.2f}"
        print(f"    {name:<10} {shown}")
    print("  문항별 통과(반복 중 통과 횟수)")
    line = []
    for item_id, info in result["per_item"].items():
        mark = "" if info["suite"] == "regression" else "*"
        line.append(f"{item_id}{mark} {info['passes']}/{info['runs']}")
    for i in range(0, len(line), 5):
        print("    " + "   ".join(line[i:i + 5]))
    low, high = result["ci95"]
    print(f"  회귀 통과율 {result['pass_rate']:.2f} (표준오차 {result['sem']:.3f}, 95% 구간 {low:.2f}~{high:.2f})"
          f" · 모든 반복 통과 {result['pass_all_runs']}/{result['regression_items']}문항")
    shown = ", ".join(f"{v:.2f}" for v in result["per_run_pass_rate"])
    print(f"  반복별 회귀 통과율: {shown}")
    if result["capability_pass_rate"] is not None:
        print(f"  능력 문항(*) 통과율 {result['capability_pass_rate']:.2f}")
    print(f"  LLM 호출 {result['llm_calls']}회 · 토큰 입력 {result['input_tokens']:,} 출력 {result['output_tokens']:,}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="jobprep 회귀 평가 실행기")
    parser.add_argument("--suite", choices=["summary", "ask", "all"], default="all")
    parser.add_argument("--prompt", default="summary_v1", help="요약 프롬프트 판본(prompts/ 아래 파일 이름)")
    parser.add_argument("--ask-prompt", default="ask_v1", help="질의응답 프롬프트 판본")
    parser.add_argument("--runs", type=int, default=5, help="같은 문항을 되풀이할 횟수")
    parser.add_argument("--backend", choices=["sim", "real"], default="sim")
    parser.add_argument("--model", default=None, help="sim이면 sim-a 또는 sim-b, real이면 LLM_MODEL을 쓴다")
    parser.add_argument("--tag", default=None, help="결과 폴더 이름(기본: 판본-모델-n반복)")
    args = parser.parse_args(argv)

    if args.backend == "sim":
        os.environ["LLM_FAKE"] = "1"
        args.model = args.model or "sim-a"
    else:
        load_env_file(EVALS_DIR.parent / ".env")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("--backend real에는 ANTHROPIC_API_KEY가 있어야 한다(.env 또는 셸). "
                             "키가 없으면 모의 모델(--backend sim)로 하고, 실제 평가는 교수 시연 기록을 읽는다.")
        os.environ["LLM_FAKE"] = "0"
        args.model = args.model or os.environ.get("LLM_MODEL", "")
        if not args.model:
            raise SystemExit("--backend real에는 LLM_MODEL 환경 변수나 --model이 있어야 한다.")
        os.environ["LLM_MODEL"] = args.model
        print(f"실제 모델 {args.model}을 부른다. 문항 수 x 반복 수 x 2(판정)만큼 호출하며 비용이 든다.")
    os.environ["PROMPT_SUMMARY"] = args.prompt
    os.environ["PROMPT_ASK"] = args.ask_prompt
    if not args.tag:
        versions = {"summary": args.prompt, "ask": args.ask_prompt, "all": f"{args.prompt}+{args.ask_prompt}"}
        args.tag = f"{versions[args.suite]}-{args.model}-n{args.runs}"

    out_dir = RUNS_DIR / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    llm_logger = logging.getLogger("jobprep.llm")
    llm_logger.setLevel(logging.INFO)
    llm_logger.propagate = False
    counter = TokenCounter()
    file_handler = logging.FileHandler(out_dir / "llm.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(LOG_FORMAT)
    llm_logger.addHandler(counter)
    llm_logger.addHandler(file_handler)

    suites = ["summary", "ask"] if args.suite == "all" else [args.suite]
    summary = {"tag": args.tag, "created": datetime.now().isoformat(timespec="seconds"),
               "backend": args.backend, "model": args.model, "runs": args.runs,
               "prompts": {"summary": args.prompt, "ask": args.ask_prompt}, "suites": {}}
    started = time.perf_counter()
    with open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as writer:
        for suite in suites:
            items = load_golden(suite)
            trials = evaluate(suite, items, args, writer, counter)
            result = summarize_trials(items, trials, args.runs)
            summary["suites"][suite] = result
            print_report(suite, result, args, args.prompt if suite == "summary" else args.ask_prompt)
    summary["seconds"] = round(time.perf_counter() - started, 2)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    file_handler.close()
    print(f"기록: {out_dir.relative_to(EVALS_DIR.parent).as_posix()}/ (records.jsonl, summary.json, llm.log)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
