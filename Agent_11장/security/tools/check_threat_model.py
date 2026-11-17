"""docs/운영/위협모델.md의 형식을 검사한다(내용의 옳고 그름은 사람이 본다). 11장 실습용.

- 양식의 아홉 절 제목이 모두 있는가
- 표마다 최소 행 수를 채웠는가: 자산 4, 진입점 4, 위협 6, 대책 6, 치명적 조합 2, 남는 위험 2
- 위협 표의 STRIDE 열이 여섯 범주 가운데 하나이고, OWASP 열에 LLM 또는 ASI 번호가 있는가
- 대책 표의 「막는 위협」이 위협 표의 ID를 가리키는가
- 양식의 자리 표시(「」, 「이름」 등)가 남아 있지 않은가
- mermaid 그림이 있는가

    python security/tools/check_threat_model.py docs/운영/위협모델.md
종료 코드: 문제가 하나라도 있으면 1.
"""

import re
import sys
from pathlib import Path

SECTIONS = ["1. 무엇을 다루는가", "2. 자산", "3. 진입점", "4. 위협과 공격 경로", "5. 대책",
            "6. 치명적 조합 점검", "7. 남는 위험", "8. 사람 승인과 감사 기록", "9. 검증"]
MIN_ROWS = {"2. 자산": 4, "3. 진입점": 4, "4. 위협과 공격 경로": 6, "5. 대책": 6,
            "6. 치명적 조합 점검": 2, "7. 남는 위험": 2}
STRIDE = {"S", "T", "R", "I", "D", "E", "스푸핑", "변조", "부인", "정보 노출", "서비스 거부", "권한 상승"}


def sections(text):
    parts = re.split(r"^## ", text, flags=re.M)
    return {p.splitlines()[0].strip(): p for p in parts[1:]}


def table_rows(block):
    rows = [l for l in block.splitlines() if l.startswith("|")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]  # 머리 줄과 구분 줄 제외


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    path = Path(argv[0] if argv else "docs/운영/위협모델.md")
    text = path.read_text(encoding="utf-8")
    found = sections(text)
    problems = []
    for name in SECTIONS:
        if not any(title.startswith(name) for title in found):
            problems.append(f"절이 없다: ## {name}")
    get = lambda name: next((b for t, b in found.items() if t.startswith(name)), "")
    for name, need in MIN_ROWS.items():
        rows = table_rows(get(name))
        if len(rows) < need:
            problems.append(f"{name}: 표의 행이 {len(rows)}개이다(최소 {need}개)")
    threat_ids = set()
    for row in table_rows(get("4. 위협과 공격 경로")):
        if len(row) < 4:
            continue
        threat_ids.add(row[0])
        categories = {c.strip() for c in re.split(r"[,·/]", row[1])}
        if not categories & STRIDE:
            problems.append(f"위협 {row[0]}: STRIDE 열이 비었거나 범주가 아니다({row[1]})")
        if not re.search(r"(LLM|ASI)\d{2}", row[2]):
            problems.append(f"위협 {row[0]}: OWASP 열에 LLM 또는 ASI 번호가 없다")
    for row in table_rows(get("5. 대책")):
        if len(row) >= 4 and not set(re.findall(r"T\d+", row[3])) & threat_ids:
            problems.append(f"대책 {row[0]}: 「막는 위협」이 위협 표의 ID를 가리키지 않는다")
    if "「" in text:
        problems.append(f"양식의 자리 표시 「…」가 {text.count('「')}곳 남아 있다")
    if "```mermaid" not in text:
        problems.append("mermaid 그림이 없다(1절)")
    for p in problems:
        print(f"위협 모델 검사: {p}")
    print(f"위협 모델 검사: 문제 {len(problems)}건" if problems else "위협 모델 검사: 통과")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
