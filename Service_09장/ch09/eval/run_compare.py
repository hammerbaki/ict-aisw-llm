"""프롬프트 판본 비교 실행기. ch09 폴더에서 실행한다.

    LLM_FAKE=1 python -m eval.run_compare v1 v2 v3 --overwrite

고정하는 것: 평가 문항 10건(eval/공고, eval/정답.json), 모델(LLM_MODEL), 채점기(eval/grader.py).
바꾸는 것: 프롬프트 판본 하나. 그래야 점수 차이를 판본 차이로 읽을 수 있다.

모의 모드(LLM_FAKE=1)는 eval/모의응답/<판본>.json에 미리 적어 둔 응답을 재생한다.
그 응답은 실제 모델의 출력이 아니라 수업용으로 만든 예시이다. 새 판본(v4 등)은 실제 호출로만 잴 수 있다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # LLM_FAKE 등. 명령 앞에 붙인 값이 앞선다

from api import llm  # noqa: E402
from api.prompts import load_prompt  # noqa: E402
from api.schema import SUMMARY_SCHEMA  # noqa: E402
from eval.grader import CHECKS, GRADER_VERSION, grade, score  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
PRICE_NOTE = "Claude Haiku 5.5, 프롬프트 10만 토큰 이하, 2026-11-14 확인. 쓰기 전에 공식 가격표에서 다시 확인한다"


def load_items() -> list[dict]:
    answers = json.loads((EVAL_DIR / "정답.json").read_text(encoding="utf-8"))
    for a in answers:
        a["공고"] = (EVAL_DIR / "공고" / f"{a['id']}.txt").read_text(encoding="utf-8")
    return answers


def run_version(version: str, items: list[dict], out: Path, use_schema: bool) -> dict:
    prompt = load_prompt(version)
    replay = None
    if llm.is_fake():
        replay_path = EVAL_DIR / "모의응답" / f"{version}.json"
        if not replay_path.exists():
            raise SystemExit(f"{version}: 모의 응답 파일이 없다({replay_path.name}). "
                             "새 판본은 LLM_FAKE=0으로 실제 호출해 잰다.")
        replay = json.loads(replay_path.read_text(encoding="utf-8"))

    work = out.with_name(out.name + "_작성중")  # 끝까지 성공했을 때만 결과 폴더 이름을 붙인다
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    rows = []
    with (work / "responses.jsonl").open("w", encoding="utf-8") as f:
        for item in items:
            try:
                result = llm.complete(prompt.system, prompt.render(item["공고"]), max_tokens=1024,
                                      json_schema=SUMMARY_SCHEMA if use_schema else None,
                                      fake_text=replay[item["id"]] if replay else None)
            except (llm.LLMError, llm.LLMRefused) as e:
                f.close()
                shutil.rmtree(work)
                raise SystemExit(f"{version} {item['id']}: {e}. 결과를 남기지 않고 멈춘다.") from None
            graded = grade(result.text, item)
            row = {"id": item["id"], "점수": score(graded), **{c: graded[c] for c in CHECKS},
                   "사유": graded["사유"], "input_tokens": result.input_tokens,
                   "output_tokens": result.output_tokens, "stop_reason": result.stop_reason,
                   "응답": result.text}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)

    n = len(rows)
    summary = {
        "판본": version,
        "바꾼 점": prompt.note,
        "합계": sum(r["점수"] for r in rows),
        "만점": n * len(CHECKS),
        "항목별": {c: sum(1 for r in rows if r[c]) for c in CHECKS},
        "평균_입력토큰": round(sum(r["input_tokens"] for r in rows) / n, 1),
        "평균_출력토큰": round(sum(r["output_tokens"] for r in rows) / n, 1),
    }
    meta = {
        "날짜": datetime.now().isoformat(timespec="seconds"),
        "모의": llm.is_fake(),
        "모델": llm.model_name(),
        "스키마_강제": use_schema,
        "채점기": GRADER_VERSION,
        "채점기_sha256": hashlib.sha256(Path(__file__).with_name("grader.py").read_bytes()).hexdigest(),
        "프롬프트_sha256": prompt.sha256,
        "문항수": n,
    }
    (work / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (work / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    work.rename(out)
    return summary


def table(summaries: list[dict], price_in: float, price_out: float) -> str:
    head = ("| 판본 | JSON | 형식 | 마감일 | 자격 | 근거 | 합계 | 평균 입력 토큰 | 평균 출력 토큰 | 1,000건 비용(USD) |\n"
            "|---|---|---|---|---|---|---|---|---|---|")
    lines = [head]
    for s in summaries:
        cost = (s["평균_입력토큰"] * price_in + s["평균_출력토큰"] * price_out) / 1_000_000 * 1000
        k = s["항목별"]
        lines.append(f"| {s['판본']} | {k['json']} | {k['형식']} | {k['마감일']} | {k['자격']} | {k['근거']} "
                     f"| {s['합계']}/{s['만점']} | {s['평균_입력토큰']} | {s['평균_출력토큰']} | {cost:.4f} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="프롬프트 판본을 같은 평가 문항으로 비교한다")
    p.add_argument("versions", nargs="+", help="비교할 판본 이름(예: v1 v2 v3)")
    p.add_argument("--out", default="results", help="결과 폴더(기본 results)")
    p.add_argument("--overwrite", action="store_true", help="같은 판본의 이전 결과를 results/_이전/으로 옮기고 다시 잰다")
    p.add_argument("--schema", action="store_true", help="구조화 출력(output_config.format)으로 형식을 강제한다")
    p.add_argument("--price-in", type=float, default=0.10, help="입력 100만 토큰당 달러")
    p.add_argument("--price-out", type=float, default=0.50, help="출력 100만 토큰당 달러")
    args = p.parse_args(argv)

    items = load_items()
    base = Path(args.out)
    summaries = []
    for version in args.versions:
        out = base / version
        if out.exists():
            if not args.overwrite:
                print(f"{out} 가 이미 있다. 다시 재려면 --overwrite 를 붙인다.", file=sys.stderr)
                return 2
            backup = base / "_이전" / f"{version}_{datetime.now():%m%d_%H%M%S}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(out), str(backup))
        summaries.append(run_version(version, items, out, args.schema))

    mode = "모의 응답 재생(실제 모델 출력 아님)" if llm.is_fake() else f"실제 호출, 모델 {llm.model_name()}"
    report = (f"# 판본 비교 결과\n\n- 실행: {datetime.now():%Y-%m-%d %H:%M}\n- 방식: {mode}\n"
              f"- 형식 강제: {'예' if args.schema else '아니오(프롬프트만)'}\n- 단가: 입력 ${args.price_in}, 출력 ${args.price_out} "
              f"/ 100만 토큰 ({PRICE_NOTE})\n\n{table(summaries, args.price_in, args.price_out)}\n")
    (base / "비교표.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
