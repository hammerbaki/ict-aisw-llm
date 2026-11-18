"""기능 하나의 월 비용을 어림한다. 요금 = 입력 토큰 × 입력 단가 + 출력 토큰 × 출력 단가.

    python tools/cost_estimate.py --input 900 --output 250 --users 300 --per-user 4 --days 30
    python tools/cost_estimate.py --from results/v3/summary.json --users 300 --per-user 4

단가 기본값은 Claude Haiku 5.5(프롬프트 10만 토큰 이하)의 2026-11-14 공식 가격이다.
가격은 바뀌므로 쓰기 전에 https://platform.claude.com/docs/en/about-claude/pricing 에서 확인한다.
출력 토큰에는 모델의 사고(thinking) 토큰도 포함되어 과금된다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def monthly_cost(input_tokens: float, output_tokens: float, calls: float,
                 price_in: float, price_out: float) -> float:
    per_call = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    return per_call * calls


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LLM 기능의 월 비용 어림")
    p.add_argument("--input", type=float, help="호출 1회의 평균 입력 토큰")
    p.add_argument("--output", type=float, help="호출 1회의 평균 출력 토큰")
    p.add_argument("--from", dest="source", help="run_compare가 남긴 summary.json에서 평균 토큰을 읽는다")
    p.add_argument("--users", type=int, default=300, help="월 사용자 수")
    p.add_argument("--per-user", type=float, default=4, help="사용자 1명의 하루 호출 수")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--price-in", type=float, default=0.10, help="입력 100만 토큰당 달러")
    p.add_argument("--price-out", type=float, default=0.50, help="출력 100만 토큰당 달러")
    p.add_argument("--krw", type=float, default=0, help="1달러의 원화 환율(주면 원화로도 보인다)")
    a = p.parse_args(argv)

    if a.source:
        s = json.loads(Path(a.source).read_text(encoding="utf-8"))
        a.input, a.output = s["평균_입력토큰"], s["평균_출력토큰"]
    if a.input is None or a.output is None:
        p.error("--input과 --output, 또는 --from 이 필요하다")

    calls = a.users * a.per_user * a.days
    cost = monthly_cost(a.input, a.output, calls, a.price_in, a.price_out)
    print(f"호출 수   : {a.users}명 × {a.per_user}회/일 × {a.days}일 = {calls:,.0f}회")
    print(f"토큰      : 입력 {a.input:,.0f} + 출력 {a.output:,.0f} (호출 1회 평균)")
    print(f"단가      : 입력 ${a.price_in} / 출력 ${a.price_out} (100만 토큰당)")
    print(f"월 비용   : ${cost:,.2f}" + (f"  (약 {cost * a.krw:,.0f}원)" if a.krw else ""))
    share_out = a.output * a.price_out / (a.input * a.price_in + a.output * a.price_out)
    print(f"출력 몫   : {share_out:.0%} (출력 단가가 입력의 {a.price_out / a.price_in:.0f}배)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
