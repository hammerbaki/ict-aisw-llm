"""운영 요건 지도(docs/운영/운영요건지도.md)가 실제 저장소와 맞는지 검사한다 (13장 11절).

지도는 「요건 → 장 → 산출물 → 확인 방법」을 표로 적은 문서이다. 문서는 쓰는 순간부터 낡기 시작하므로,
기계로 확인할 수 있는 것만이라도 확인한다.

검사 항목
  M1  네 운영 요건(보안, 신뢰성, 일관성, 재현성)마다 표의 행이 하나 이상 있다
  M2  표의 「산출물」 칸에 백틱(`)으로 적은 경로가 저장소에 있다(* 가 든 경로는 glob으로 찾는다)
  M3  「확인 방법」 칸이 비어 있지 않다
  M4  「자동화」 칸의 값이 CI, 훅, 설정, 배포, 수동 가운데 하나 이상을 담고 있다
  M5  「1장의 요건」 칸에 1장의 요건 ID(OR-SEC-01처럼 OR-<SEC|REL|CON|REP>-NN)가 있고, 분류가 「요건」 칸과 맞는다
      (보안 SEC, 신뢰성 REL, 일관성 CON, 재현성 REP). docs/운영/운영요건.md가 있으면 그 문서에 있는 ID인지도 본다

쓰는 법 (저장소 폴더에서)
    python ops/map/check_map.py                      docs/운영/운영요건지도.md 를 검사한다
    python ops/map/check_map.py 다른/지도.md
문제가 있으면 종료 코드 1이다.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT = ROOT / "docs" / "운영" / "운영요건지도.md"
REQUIREMENT_DOC = ROOT / "docs" / "운영" / "운영요건.md"   # 1장의 운영 요건 명세
REQUIREMENTS = ("보안", "신뢰성", "일관성", "재현성")
AUTOMATION = ("CI", "훅", "설정", "배포", "수동")
CODE = re.compile(r"`([^`]+)`")
REQ_ID = re.compile(r"\bOR-(SEC|REL|CON|REP)-\d{2}\b")
CATEGORY = {"보안": "SEC", "신뢰성": "REL", "일관성": "CON", "재현성": "REP"}


def looks_like_path(text):
    return ("/" in text or re.search(r"\.[A-Za-z]{2,5}$", text)) and " " not in text and not text.startswith("-")


def exists(path):
    if "*" in path:
        return any(ROOT.glob(path))
    return (ROOT / path.rstrip("/")).exists()


def rows(text):
    """머리 줄에 「요건」과 「산출물」이 있는 표의 행을 {열 이름: 값} 목록으로 돌려준다."""
    header, found = None, []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            if "요건" in cells and "산출물" in cells:
                header = cells
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        found.append(dict(zip(header, cells)))
    return found


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0]) if args else DEFAULT
    if not path.is_file():
        print(f"지도 파일이 없다: {path}")
        return 2
    table = rows(path.read_text(encoding="utf-8"))
    problems = []
    for requirement in REQUIREMENTS:
        if not any(requirement in row.get("요건", "") for row in table):
            problems.append(("M1", f"「{requirement}」의 행이 없다"))
    known = ({m.group(0) for m in REQ_ID.finditer(REQUIREMENT_DOC.read_text(encoding="utf-8"))}
             if REQUIREMENT_DOC.is_file() else None)
    checked = 0
    for number, row in enumerate(table, 1):
        label = f"{number}행({row.get('요건', '?')})"
        for item in CODE.findall(row.get("산출물", "")):
            if looks_like_path(item):
                checked += 1
                if not exists(item):
                    problems.append(("M2", f"{label}: 경로가 없다 `{item}`"))
        if not row.get("확인 방법", "").strip():
            problems.append(("M3", f"{label}: 확인 방법이 비어 있다"))
        if not any(word in row.get("자동화", "") for word in AUTOMATION):
            problems.append(("M4", f"{label}: 자동화 칸에 CI, 훅, 설정, 배포, 수동 가운데 하나를 적는다"))
        ids = [m.group(0) for m in REQ_ID.finditer(row.get("1장의 요건", ""))]
        want = next((code for name, code in CATEGORY.items() if name in row.get("요건", "")), None)
        if not ids:
            problems.append(("M5", f"{label}: 1장의 요건 ID(OR-…)가 없다"))
        for req_id in ids:
            if want and req_id.split("-")[1] != want:
                problems.append(("M5", f"{label}: {req_id}의 분류가 요건({row.get('요건')}={want})과 다르다"))
            if known is not None and req_id not in known:
                problems.append(("M5", f"{label}: {req_id}가 docs/운영/운영요건.md에 없다"))
    for code, detail in problems:
        print(f"{code}  {detail}")
    print(f"지도 검사: 행 {len(table)}개, 경로 {checked}개 확인, 문제 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
