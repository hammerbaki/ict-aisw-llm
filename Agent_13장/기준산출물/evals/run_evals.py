"""회귀 평가: 골든 세트를 채점하고 기준 결과와 비교한다 (12장 기준산출물의 간단한 견본).

12장을 마친 학습자는 12장의 evals.run과 evals.gate를 쓴다(ops/ci/eval_gate.sh가 고른다).
이 견본은 12장을 마치지 못한 학습자를 위해 13장의 CI가 부를 수 있는 최소 형태이다.

- 골든 세트: evals/golden.jsonl (한 줄에 한 문항)
- 기준 결과: evals/regression_baseline.json (사람이 검토하고 커밋한 「지금까지 통과하던 문항」)
  12장의 evals/baseline.json(evals.gate의 기준선)과 섞이지 않도록 이름을 달리하였다.
- 이번 결과: evals/results/latest.json (커밋하지 않는다)

쓰는 법 (저장소 폴더에서)
    python evals/run_evals.py                    채점하고 결과를 쓴다(종료 코드는 언제나 0)
    python evals/run_evals.py --check            기준과 비교해 회귀가 있으면 종료 코드 1
    python evals/run_evals.py --update-baseline  이번 결과를 새 기준으로 쓴다(검토한 뒤에만)

키 없이 돈다. EVAL_REAL=1이 아니면 LLM_FAKE=1(모의 모드)로 강제한다. 실제 모델로 돌리는 평가는
비용이 들고 결과가 흔들리므로 CI의 필수 검사에 넣지 않는다(12장).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
GOLDEN = EVALS / "golden.jsonl"
BASELINE = EVALS / "regression_baseline.json"
LATEST = EVALS / "results" / "latest.json"

# 앱을 불러오기 전에 환경을 정한다(tests/conftest.py와 같은 조건).
if os.environ.get("EVAL_REAL") != "1":
    os.environ["LLM_FAKE"] = "1"
os.environ.setdefault("EMBED_BACKEND", "fallback")
os.environ["RAG_INDEX_PATH"] = os.path.join(tempfile.mkdtemp(prefix="jobprep-eval-"), "index.json")
sys.path.insert(0, str(ROOT))

from api import jobs, llm  # noqa: E402
from api.ask import NOT_FOUND, answer_question  # noqa: E402
from api.summary import SummaryError, summarize  # noqa: E402


def load_golden(path=GOLDEN):
    items = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip() and not line.lstrip().startswith("#"):
            item = json.loads(line)
            item.setdefault("id", f"line-{number}")
            items.append(item)
    return items


def job_text(job_id):
    job = jobs.get_job(job_id)
    return f"{job['title']} / {job['company']}\n마감일: {job['deadline']}\n{job['description']}", job


def grade_ask(item):
    """질의응답 문항: 근거 문서가 맞는가, 또는 범위 밖 질문에 「자료에 없습니다.」로 답하는가."""
    result = answer_question(item["question"])
    expect = item["expect"]
    if expect.get("not_found"):
        ok = result["answer"] == NOT_FOUND and result["sources"] == []
        return ok, "" if ok else f"범위 밖인데 답함: {result['answer'][:30]}"
    if result["answer"] == NOT_FOUND:
        return False, "근거를 찾지 못함(자료에 없습니다.)"
    sources = [s["source"] for s in result["sources"]]
    ok = bool(sources) and sources[0] == expect["source"]
    return ok, "" if ok else f"근거 문서 불일치: {sources[:1]}"


def grade_summary(item):
    """요약 문항: 구조 검사를 통과하고, 마감일이 공고와 같고, 핵심 업무가 있는가."""
    text, job = job_text(item["job_id"])
    try:
        result = summarize(text)
    except (SummaryError, llm.LLMError) as error:
        return False, f"요약 실패: {type(error).__name__}"
    problems = []
    if result["deadline"] != job["deadline"]:
        problems.append(f"마감일 {result['deadline']} != {job['deadline']}")
    if len(result["duties"]) < item["expect"].get("min_duties", 1):
        problems.append("핵심 업무 부족")
    return not problems, "; ".join(problems)


GRADERS = {"ask": grade_ask, "summary": grade_summary}


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run():
    rows = []
    for item in load_golden():
        ok, reason = GRADERS[item["kind"]](item)
        rows.append({"id": item["id"], "kind": item["kind"], "pass": ok, "reason": reason})
    passed = sum(r["pass"] for r in rows)
    return {
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": git_commit(),
        "model": llm.model_name(),
        "prompts": {"summary": llm.prompt_version("summary"), "ask": llm.prompt_version("ask")},
        "total": len(rows),
        "passed": passed,
        "rows": rows,
    }


def compare(report, baseline):
    """기준에서 통과하던 문항이 지금 떨어졌으면 회귀이다. 통과율이 내려가도 회귀이다."""
    now_pass = {r["id"] for r in report["rows"] if r["pass"]}
    regressed = sorted(set(baseline["passed_ids"]) - now_pass)
    rate = report["passed"] / report["total"] if report["total"] else 0.0
    problems = []
    if regressed:
        problems.append(f"기준에서 통과하던 문항이 실패: {', '.join(regressed)}")
    if rate + 1e-9 < baseline["pass_rate"]:
        problems.append(f"통과율 하락: {baseline['pass_rate']:.2f} -> {rate:.2f}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="jobprep 회귀 평가 (모의 모드)")
    parser.add_argument("--check", action="store_true", help="기준과 비교해 회귀가 있으면 종료 코드 1")
    parser.add_argument("--update-baseline", action="store_true", help="이번 결과를 새 기준으로 쓴다")
    args = parser.parse_args(argv)

    report = run()
    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for row in report["rows"]:
        mark = "통과" if row["pass"] else "실패"
        print(f"{mark}  {row['id']:<12} {row['reason']}")
    print(f"합계: {report['passed']}/{report['total']} 통과 "
          f"(model={report['model']}, summary={report['prompts']['summary']}, ask={report['prompts']['ask']})")

    if args.update_baseline:
        baseline = {
            "passed_ids": sorted(r["id"] for r in report["rows"] if r["pass"]),
            "pass_rate": round(report["passed"] / report["total"], 4),
            "commit": report["commit"],
            "prompts": report["prompts"],
        }
        BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"기준을 새로 썼다: {BASELINE.relative_to(ROOT).as_posix()}")
        return 0

    if args.check:
        if not BASELINE.exists():
            print("기준 파일이 없다: python evals/run_evals.py --update-baseline 으로 먼저 만든다(evals/regression_baseline.json)")
            return 2
        problems = compare(report, json.loads(BASELINE.read_text(encoding="utf-8")))
        if problems:
            for problem in problems:
                print(f"회귀: {problem}")
            return 1
        print("회귀 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
