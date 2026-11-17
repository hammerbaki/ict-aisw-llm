"""LLM 호출 기록(api/logs/llm_calls.jsonl)을 변형별로 모아 호출 수, 토큰, 어림 비용을 낸다.

    python 도구/token_report.py 기록1.jsonl [기록2.jsonl ...] --tasks 6 --price-in 1.0 --price-out 5.0

--tasks는 기록에 담긴 과업 수(측정 스크립트의 준비 횟수 + 반복 횟수)다. 과업당 값을 낼 때 나눈다.
--price-in, --price-out은 백만 토큰당 달러 단가다. 수업 직전에 공식 가격표에서 확인해 넣는다.
모의 모드 기록의 토큰은 글자 수로 어림한 값이므로 변형끼리 견주는 데만 쓴다.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import utf8_stdout  # noqa: E402


def main() -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--tasks", type=int, default=0)
    ap.add_argument("--price-in", type=float, default=0.0)
    ap.add_argument("--price-out", type=float, default=0.0)
    ap.add_argument("--purpose", help="이 문자열로 시작하는 용도만 센다(예: feedback)")
    args = ap.parse_args()

    agg = defaultdict(lambda: {"calls": 0, "failed": 0, "in": 0, "out": 0, "ms": 0, "fake": False})
    for log in args.logs:
        for line in Path(log).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if args.purpose and not r["purpose"].startswith(args.purpose):
                continue
            a = agg[r["variant"]]
            a["calls"] += 1
            a["failed"] += 0 if r["ok"] else 1
            a["in"] += r["input_tokens"]
            a["out"] += r["output_tokens"]
            a["ms"] += r["latency_ms"]
            a["fake"] = a["fake"] or r["fake"]

    print("| 변형 | 호출 | 실패 | 입력 토큰 | 출력 토큰 | 과업당 호출 | 과업당 토큰 | 과업당 비용(USD) |")
    print("|---|---|---|---|---|---|---|---|")
    for variant, a in sorted(agg.items()):
        t = args.tasks or 1
        cost = (a["in"] * args.price_in + a["out"] * args.price_out) / 1_000_000 / t
        mark = " (모의·어림)" if a["fake"] else ""
        print(
            f"| {variant}{mark} | {a['calls']} | {a['failed']} | {a['in']} | {a['out']} | "
            f"{a['calls'] / t:.1f} | {(a['in'] + a['out']) / t:.0f} | {cost:.6f} |"
        )
    if not args.tasks:
        print("\n--tasks를 주지 않아 과업당 값은 전체 합계다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
