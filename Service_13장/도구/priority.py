"""사용성 문제 목록의 우선순위를 낸다.

    python priority.py 문제목록.md [--md]
    python priority.py 문제목록.csv [--md]

입력은 둘 가운데 하나이다.
  - 마크다운 문제 목록(13장의 `문제목록_양식.md`로 만든 것). 첫 표의 머리글에
    번호, 문제, 출처, 휴리스틱, 심각도, 빈도가 있어야 한다. 다른 열(점수, 관련 요구)은 읽지 않는다.
    칸이 빈 줄(양식의 빈 줄)은 건너뛴다.
  - CSV. 머리글: ID,문제,출처,휴리스틱,심각도,빈도

심각도는 0~4(Nielsen의 척도), 빈도는 1~3(1 드묾, 2 가끔, 3 자주)이다.
우선순위 점수 = 심각도 x 빈도. 심각도 0(문제 아님)은 목록에서 뺀다.
심각도 4는 점수와 관계없이 맨 앞에 둔다. 점수가 같으면 심각도가 높은 쪽이 앞서고,
그것도 같으면 번호 순서이다.

종료 코드: 0 정상, 1 사용법·파일 없음, 2 입력 오류.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

COLUMNS = ["ID", "문제", "출처", "휴리스틱", "심각도", "빈도"]


class PriorityError(ValueError):
    """입력이 형식에 맞지 않을 때 낸다."""


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_markdown(path):
    """첫 표를 (줄 번호, 행 사전)의 목록으로 읽는다. 머리글의 「번호」를 ID로 본다."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            # 머리글 뒤의 괄호 설명(예: 「출처 (AI(번호) 재현됨 / 직접)」)은 떼어 낸다.
            header = [h.split(" (")[0].strip() for h in _cells(line)]
            header = ["ID" if h == "번호" else h for h in header]
            break
    else:
        raise PriorityError("표를 찾지 못했다")
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        raise PriorityError(f"머리글에 없는 열: {', '.join(missing)}")
    rows = []
    for j in range(i + 2, len(lines)):
        if not lines[j].lstrip().startswith("|"):
            break
        cells = _cells(lines[j])
        row = dict(zip(header, cells + [""] * (len(header) - len(cells))))
        if not any(row[c] for c in COLUMNS[1:]):
            continue
        rows.append((j + 1, row))
    return rows


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise PriorityError(f"머리글에 없는 열: {', '.join(missing)}")
        return [(n, r) for n, r in enumerate(reader, start=2) if any((v or "").strip() for v in r.values())]


def _int(row, key, line, low, high):
    text = (row[key] or "").strip()
    try:
        value = int(text)
    except ValueError:
        raise PriorityError(f"{line}번째 줄의 {key}: 정수가 아니다 ({text!r})") from None
    if not low <= value <= high:
        raise PriorityError(f"{line}번째 줄의 {key}: {low}~{high} 범위 밖이다 ({value})")
    return value


def load_problems(path):
    rows = read_markdown(path) if str(path).lower().endswith(".md") else read_csv(path)
    if not rows:
        raise PriorityError("자료가 한 줄도 없다")
    problems = []
    for line, row in rows:
        problems.append({
            "ID": row["ID"].strip(),
            "문제": row["문제"].strip(),
            "출처": row["출처"].strip(),
            "휴리스틱": row["휴리스틱"].strip(),
            "심각도": _int(row, "심각도", line, 0, 4),
            "빈도": _int(row, "빈도", line, 1, 3),
        })
    ids = [p["ID"] for p in problems]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated:
        raise PriorityError(f"번호가 겹친다: {', '.join(duplicated)}")
    return problems


def severity_counts(problems):
    counts = Counter(p["심각도"] for p in problems)
    return {level: counts.get(level, 0) for level in (4, 3, 2, 1, 0)}


def prioritize(problems):
    real = [dict(p, 점수=p["심각도"] * p["빈도"]) for p in problems if p["심각도"] > 0]
    return sorted(real, key=lambda p: (p["심각도"] != 4, -p["점수"], -p["심각도"], p["ID"]))


def report(problems, markdown=False):
    ranked = prioritize(problems)
    lines = ["심각도별 문제 수: " + ", ".join(f"{k}={v}" for k, v in severity_counts(problems).items()), ""]
    if markdown:
        lines.append("| 순위 | 번호 | 문제 | 출처 | 휴리스틱 | 심각도 | 빈도 | 점수 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for rank, p in enumerate(ranked, start=1):
            lines.append(f"| {rank} | {p['ID']} | {p['문제']} | {p['출처']} | {p['휴리스틱']} "
                         f"| {p['심각도']} | {p['빈도']} | {p['점수']} |")
    else:
        for rank, p in enumerate(ranked, start=1):
            lines.append(f"{rank:>2}. [{p['점수']:>2}] {p['ID']} (심각도 {p['심각도']} x 빈도 {p['빈도']}) {p['문제']}")
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
        print(report(load_problems(path), "--md" in argv))
    except PriorityError as e:
        print(f"오류: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
