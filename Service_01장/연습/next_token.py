"""다음 토큰 선택의 모의 실험 (실제 모델을 부르지 않는다)

LLM이 다음 토큰을 고르는 마지막 단계(샘플링)만 떼어 내어 흉내 낸다.
확률표는 설명을 위해 집필자가 정한 값이며, 실제 모델의 확률이 아니다.

temperature는 샘플링이라는 개념을 보이기 위한 모의 값이다. 현재 Claude API
(2026-10-21 판)와 anthropic SDK 2.x는 temperature를 요청 인자로 받지 않는다.
이 판에서 temperature, top_p, top_k를 보내면 기본값이라도 400 오류가 나고,
요청은 기본값(temperature 1.0)으로 샘플링한다. 실제 서비스에서 이 값을 정하지
않는 까닭과 일관성을 얻는 다른 방법은 10장에서 다룬다.

사용법:
    python next_token.py --list
    python next_token.py --context 수도 --show
    python next_token.py --context 수도 --temperature 0 --trials 10
    python next_token.py --context 수도 --temperature 1 --trials 10 --seed 7
"""
import argparse
import random
import sys
from collections import Counter

# 문맥별 다음 토큰 후보와 확률(모의 값). 합은 1이다.
TABLES = {
    "수도": {
        "prompt": "대한민국의 수도는",
        "probs": {"서울": 0.86, "세종": 0.06, "부산": 0.04, "어디": 0.04},
    },
    "마감": {
        "prompt": "채용 공고의 마감일이 지나면 지원서는",
        "probs": {"접수되지": 0.62, "제출할": 0.20, "자동으로": 0.10, "다시": 0.08},
    },
    "맥북": {
        # 존재하지 않는 사건을 물어도 후보에는 '그럴듯한 연도'만 있다. 환각의 구조를 보이는 예.
        "prompt": "조선왕조실록에 기록된 세종대왕의 맥북 던짐 사건은",
        "probs": {"1443년에": 0.41, "1446년에": 0.33, "기록되어": 0.16, "실록에": 0.10},
    },
}


def apply_temperature(probs, temperature):
    """temperature로 확률 분포의 모양을 바꾼다. 0이면 가장 높은 후보 하나만 남긴다.

    모의 실험의 계산이다. 현재 API(2026-10-21 판)에서는 이 값을 요청에 넣을 수 없다.
    """
    if temperature <= 0:
        best = max(probs, key=probs.get)
        return {token: (1.0 if token == best else 0.0) for token in probs}
    weights = {token: p ** (1.0 / temperature) for token, p in probs.items()}
    total = sum(weights.values())
    return {token: w / total for token, w in weights.items()}


def sample(dist, rng):
    tokens = list(dist)
    return rng.choices(tokens, weights=[dist[t] for t in tokens], k=1)[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="다음 토큰 선택의 모의 실험")
    parser.add_argument("--list", action="store_true", help="준비된 문맥 목록을 보인다")
    parser.add_argument("--context", default="수도", help="문맥 이름 (--list로 확인)")
    parser.add_argument("--temperature", type=float, default=1.0, help="0 이상. 기본 1.0. 모의 값이며 현재 API(2026-10-21 판)는 이 값을 받지 않는다")
    parser.add_argument("--trials", type=int, default=10, help="반복 횟수. 기본 10")
    parser.add_argument("--seed", type=int, help="난수 씨앗. 주면 같은 결과가 재현된다")
    parser.add_argument("--show", action="store_true", help="확률표만 보인다")
    args = parser.parse_args(argv)

    if args.list:
        for name, table in TABLES.items():
            print(f"{name:<4} {table['prompt']}")
        return 0
    if args.context not in TABLES:
        print(f"오류: 없는 문맥입니다: {args.context} (--list로 확인)", file=sys.stderr)
        return 1
    if args.temperature < 0:
        print("오류: temperature는 0 이상이어야 합니다.", file=sys.stderr)
        return 1

    table = TABLES[args.context]
    dist = apply_temperature(table["probs"], args.temperature)
    print(f"문맥: {table['prompt']} ___")
    print(f"temperature={args.temperature}")
    for token, p in sorted(dist.items(), key=lambda kv: -kv[1]):
        bar = "#" * round(p * 30)
        print(f"  {token:<6} {p:5.2f} {bar}")
    if args.show:
        return 0

    rng = random.Random(args.seed)
    picks = [sample(dist, rng) for _ in range(args.trials)]
    print(f"{args.trials}회 선택: {' '.join(picks)}")
    counts = Counter(picks)
    print("집계: " + ", ".join(f"{t} {n}회" for t, n in counts.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
