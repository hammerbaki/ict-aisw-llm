"""SUS(System Usability Scale) 점수를 계산한다.

입력은 CSV 파일 하나다. 첫 줄은 머리글 `참가자,Q1,Q2,...,Q10`이고,
한 줄에 참가자 한 명의 응답(1~5의 정수 열 개)을 적는다.

    python sus.py 응답.csv           점수 표를 출력한다
    python sus.py 응답.csv --md      SUS.md에 붙일 마크다운 표를 출력한다

점수 계산(Brooke, 1996):
  홀수 문항(1, 3, 5, 7, 9)은 응답에서 1을 뺀다.
  짝수 문항(2, 4, 6, 8, 10)은 5에서 응답을 뺀다.
  열 값을 더해 2.5를 곱한다. 결과는 0~100이며 백분율이 아니다.
"""
import csv
import statistics
import sys
from pathlib import Path

ITEMS = [f"Q{i}" for i in range(1, 11)]
AVERAGE = 68  # Sauro(2011)가 보고한 여러 연구의 평균. 해석의 기준선으로만 쓴다


class SusError(ValueError):
    """응답이 SUS의 형식에 맞지 않을 때 낸다."""


def sus_score(responses):
    """응답 열 개(1~5의 정수)를 받아 SUS 점수(0~100)를 돌려준다."""
    if len(responses) != 10:
        raise SusError(f"응답은 10개여야 한다 (받은 개수: {len(responses)})")
    total = 0
    for number, value in enumerate(responses, start=1):
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            raise SusError(f"Q{number}의 응답은 1~5의 정수여야 한다 (받은 값: {value!r})")
        total += (value - 1) if number % 2 == 1 else (5 - value)
    return total * 2.5


def load(path):
    """CSV를 읽어 [(참가자, [응답 10개]), ...]를 돌려준다."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ["참가자", *ITEMS] if c not in (reader.fieldnames or [])]
        if missing:
            raise SusError(f"머리글에 없는 열: {', '.join(missing)}")
        for line, row in enumerate(reader, start=2):
            name = (row["참가자"] or "").strip()
            if not name:
                continue
            values = []
            for item in ITEMS:
                text = (row[item] or "").strip()
                if not text.isdigit():
                    raise SusError(f"{line}번째 줄 {name}의 {item}: 숫자가 아니거나 비어 있다 ({text!r})")
                values.append(int(text))
            rows.append((name, values))
    if not rows:
        raise SusError("응답이 한 줄도 없다")
    return rows


def summarize(scores):
    """점수 목록의 요약(개수, 평균, 최솟값, 최댓값)을 돌려준다."""
    return {
        "n": len(scores),
        "mean": statistics.fmean(scores),
        "min": min(scores),
        "max": max(scores),
    }


def report(rows, markdown=False):
    scored = [(name, values, sus_score(values)) for name, values in rows]
    summary = summarize([s for _, _, s in scored])
    lines = []
    if markdown:
        lines.append("| 참가자 | " + " | ".join(ITEMS) + " | SUS |")
        lines.append("|---" * 12 + "|")
        for name, values, score in scored:
            lines.append(f"| {name} | " + " | ".join(str(v) for v in values) + f" | {score:.1f} |")
    else:
        for name, values, score in scored:
            lines.append(f"{name:<8} {' '.join(str(v) for v in values)}  ->  {score:5.1f}")
    lines.append("")
    side = "위" if summary["mean"] > AVERAGE else ("같음" if summary["mean"] == AVERAGE else "아래")
    lines.append(
        f"참가자 {summary['n']}명, 평균 {summary['mean']:.1f}점 "
        f"(최저 {summary['min']:.1f}, 최고 {summary['max']:.1f}). "
        f"기준선 {AVERAGE}점보다 {side}."
    )
    if summary["n"] < 5:
        lines.append("주의: 참가자가 5명 미만이다. 평균은 방향을 보는 참고 값이며 다른 제품과 견주는 근거로 쓰지 않는다.")
    return "\n".join(lines)


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 1
    path = Path(args[0])
    if not path.exists():
        print(f"파일이 없다: {path}")
        return 1
    try:
        rows = load(path)
        print(report(rows, markdown="--md" in argv))
    except SusError as e:
        print(f"오류: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
