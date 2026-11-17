"""가짜 기획 에이전트: ISSUE-07의 견본 계획서와 작업 카드를 인계 폴더에 놓고, 명세서에 새 요구를 「미구현」으로 더한다.

실제 수업에서는 Claude Code의 planner 에이전트가 계획서를 쓴다(6절). 이 스크립트는 모델 없이도
같은 결과물로 다음 단계를 진행할 수 있게 하는 대역이다. 커밋하지 않는다. 사람이 읽고 승인한 뒤 커밋한다.

사용법 (저장소 맨 위에서, 통합 브랜치 feat/issue-07에 있는 상태로)
    python ops/multi/fake/plan_agent.py ISSUE-07
"""

import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
SPEC = ROOT / "docs" / "요구사항명세서.md"
ANCHOR = "| REQ-FAV-02 "
NEW_ROWS = [
    "| REQ-FAV-03 | 이벤트 | 사용자가 공고 번호 목록으로 관심 공고 내보내기를 요청하면, 시스템은 그 공고들을 CSV 파일로 제공해야 한다. "
    "| `GET /api/favorites/export?ids=3,1`이 200, `text/csv`, 내려받기 머리글을 돌려준다. 본문은 BOM으로 시작하고 "
    "머리줄 `id,title,company,field,deadline,days_left` 다음에 마감일 오름차순의 행이 온다. 같은 번호는 한 번만 넣는다 "
    "| **미구현** | `test_favorites_export.py` |",
    "| REQ-FAV-04 | 원치 않는 상황 | 만약 내보낼 번호 목록이 비었거나, 양의 정수가 아닌 값이 있거나, 30개를 넘으면 422로, "
    "없는 공고 번호가 있으면 404로 응답해야 한다. | 404의 `detail`에 없는 번호가 있다. 30개는 받아들인다 "
    "| **미구현** | `test_favorites_export.py` |",
    "| REQ-FAV-05 | 이벤트 | 사용자가 목록 화면의 '관심 공고 내보내기'를 누르면, 시스템은 관심 공고의 CSV 파일을 내려받게 해야 한다. "
    "관심 공고가 없으면 API를 부르지 않고 그 사실을 알려야 한다. | 단추 `#export-favorites`, 스크립트 `web/js/export.js` "
    "| **미구현** | `test_web_export.py`(정적 검사) |",
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    issue = sys.argv[1]
    source = HERE.parent / "견본" / issue
    target = ROOT / "docs" / "운영" / "인계" / issue
    if not source.is_dir():
        print(f"오류: 견본 {source}가 없다")
        return 2
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.md")):
        dest = target / path.name
        if dest.exists():
            print(f"있음  {dest.relative_to(ROOT).as_posix()} (덮어쓰지 않는다)")
        else:
            shutil.copyfile(path, dest)
            print(f"씀    {dest.relative_to(ROOT).as_posix()}")

    text = SPEC.read_text(encoding="utf-8")
    if "| REQ-FAV-03 " in text:
        print("있음  명세서에 REQ-FAV-03이 이미 있다")
    else:
        lines = text.split("\n")
        at = next((i for i, line in enumerate(lines) if line.startswith(ANCHOR)), None)
        if at is None:
            print(f"오류: 명세서에서 {ANCHOR.strip()} 행을 찾지 못하였다")
            return 1
        lines[at + 1:at + 1] = NEW_ROWS
        SPEC.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print("고침  docs/요구사항명세서.md (REQ-FAV-03~05를 미구현으로 더함)")
    print("다음: 계획서를 읽고 「- 승인 대기」 줄을 「- 승인: 이름, 날짜」로 고친 뒤 커밋한다")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
