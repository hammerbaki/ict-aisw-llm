"""LLM 기능 하나의 월 호출 비용 어림 (실제 모델을 부르지 않는다)

토큰 단가는 실행할 때 인자로 준다. 단가는 바뀌므로 코드에 적어 두지 않는다.
단가의 출처: Claude API 문서 「Models overview」의 Pricing 행 (USD / 백만 토큰).

사용법:
    python cost.py --input 2000 --output 300 --users 300 --per-day 5 --in-price 2 --out-price 10
"""
import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="LLM 기능의 월 호출 비용 어림")
    parser.add_argument("--input", type=int, required=True, help="호출 1회의 입력 토큰 수")
    parser.add_argument("--output", type=int, required=True, help="호출 1회의 출력 토큰 수")
    parser.add_argument("--users", type=int, default=1, help="하루 이용자 수")
    parser.add_argument("--per-day", type=int, default=1, help="이용자 1명의 하루 호출 수")
    parser.add_argument("--days", type=int, default=30, help="한 달의 일수. 기본 30")
    parser.add_argument("--in-price", type=float, required=True, help="입력 단가 USD/백만 토큰")
    parser.add_argument("--out-price", type=float, required=True, help="출력 단가 USD/백만 토큰")
    args = parser.parse_args(argv)

    per_call = (args.input * args.in_price + args.output * args.out_price) / 1_000_000
    calls = args.users * args.per_day * args.days
    total = per_call * calls
    print(f"호출 1회: 입력 {args.input:,} + 출력 {args.output:,} 토큰 -> ${per_call:.4f}")
    print(f"월 호출 수: {args.users:,}명 x {args.per_day}회 x {args.days}일 = {calls:,}회")
    print(f"월 비용 어림: ${total:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
