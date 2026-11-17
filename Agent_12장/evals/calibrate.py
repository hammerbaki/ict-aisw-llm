"""판정자 보정: 사람이 판정한 표본과 판정자의 판정을 대조한다.

사용법
    python -m evals.calibrate                  기본 기준값(judge.SUPPORT_MIN)으로 대조
    python -m evals.calibrate --support 0.35   모의 판정자의 기준값을 바꾸어 대조
    python -m evals.calibrate --numbers        숫자 대조 규칙을 더해 대조

표본은 evals/calibration/judge_sample.jsonl이다. 한 줄이 출력 하나이며, human 칸에 사람이 내린
판정(pass 또는 fail)과 그 까닭(why)이 있다. 일치율과 코언의 카파(우연히 일치할 몫을 뺀 일치도)를
내고, 판정이 엇갈린 표본을 보인다. 엇갈린 표본을 읽고 기준표나 판정 방식을 고친 뒤 다시 잰다.
"""

import argparse
import json
import sys
from pathlib import Path

from evals import judge
from evals.run import load_golden

SAMPLE = Path(__file__).resolve().parent / "calibration" / "judge_sample.jsonl"


def cohen_kappa(pairs):
    """(사람, 판정자) 쌍의 목록으로 코언의 카파를 계산한다. 값은 pass와 fail 둘이다."""
    n = len(pairs)
    observed = sum(1 for h, j in pairs if h == j) / n
    expected = 0.0
    for label in ("pass", "fail"):
        expected += (sum(1 for h, _ in pairs if h == label) / n) * (sum(1 for _, j in pairs if j == label) / n)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def main(argv=None):
    parser = argparse.ArgumentParser(description="판정자와 사람 판정의 대조")
    parser.add_argument("--support", type=float, default=judge.SUPPORT_MIN, help="모의 판정자의 기준값")
    parser.add_argument("--numbers", action="store_true", help="숫자가 근거에 있는지도 본다")
    args = parser.parse_args(argv)

    golden = {item["id"]: item for item in load_golden("summary")}
    pairs, rows = [], []
    for line in SAMPLE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        evidence = golden[case["item"]]["input"]
        verdict, reason = judge.mock_judge(evidence, "\n".join(case["output"]), support_min=args.support,
                                           check_numbers=args.numbers)
        pairs.append((case["human"], verdict))
        rows.append((case, verdict, reason))

    matrix = {(h, j): 0 for h in ("pass", "fail") for j in ("pass", "fail")}
    for pair in pairs:
        matrix[pair] += 1
    agree = sum(1 for h, j in pairs if h == j)
    extra = ", 숫자 대조" if args.numbers else ""
    print(f"판정자: 모의 판정자(기준값 {args.support:.2f}{extra}) · 표본 {len(pairs)}개")
    print("               판정자 pass  판정자 fail")
    print(f"  사람 pass    {matrix[('pass', 'pass')]:>10}  {matrix[('pass', 'fail')]:>10}")
    print(f"  사람 fail    {matrix[('fail', 'pass')]:>10}  {matrix[('fail', 'fail')]:>10}")
    print(f"일치율 {agree / len(pairs):.2f} · 코언의 카파 {cohen_kappa(pairs):.2f}")
    for case, verdict, reason in rows:
        if verdict != case["human"]:
            print(f"  엇갈림 {case['id']}({case['item']}): 사람 {case['human']}, 판정자 {verdict}"
                  f" — 사람의 까닭: {case['why']}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
