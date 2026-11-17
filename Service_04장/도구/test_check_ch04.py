"""check_ch04.py 의 테스트. 키트 폴더에서 `python -m pytest -q 도구` 로 실행한다."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ch04 as c  # noqa: E402

KIT = Path(__file__).resolve().parents[1]
SOURCES = """
| 기호 | 자료 이름 | 주소 | 확인 날짜 |
|---|---|---|---|
| S1 | 표 | https://example.org/a | 2026-11-14 |
"""


def test_수치에_출처가_있으면_통과():
    problems, n = c.scan("- 전문대학 재적학생은 504,897명이다 [S1].\n" + SOURCES)
    assert problems == []
    assert n == 1


def test_출처_없는_수치를_찾는다():
    problems, _ = c.scan("- 시장 규모는 약 5,000억 원이다.\n" + SOURCES)
    assert any("5,000억 원" in p for p in problems)


def test_연도와_날짜는_수치로_보지_않는다():
    problems, _ = c.scan("- 2026년 5월 조사, 2026-11-14 확인 [S1].\n" + SOURCES)
    assert [p for p in problems if "수치" in p] == []


def test_가정_기호가_있으면_통과():
    text = "- 채용률 10%로 둔다 [가정 A1].\n| 기호 | 가정 |\n|---|---|\n| A1 | 채택률 |\n" + SOURCES
    problems, _ = c.scan(text)
    assert [p for p in problems if "수치" in p] == []


def test_출처_표에_없는_기호():
    problems, _ = c.scan("- 72.1%이다 [S9].\n" + SOURCES)
    assert any("[S9]" in p for p in problems)


def test_출처에_확인_날짜가_없으면_미통과():
    text = "- 72.1%이다 [S1].\n| 기호 | 주소 | 확인 날짜 |\n|---|---|---|\n| S1 | https://x.org | 모름 |\n"
    problems, _ = c.scan(text)
    assert any("확인 날짜" in p for p in problems)


def test_비교표_크기():
    head = "| 기능 | A | B | C | D | E | 비고 |\n|---|---|---|---|---|---|---|\n"
    rows = "".join(f"| 기능{i} | ○ | △ | - | ○ | ○ | |\n" for i in range(10))
    problems, cols, n = c.check_table(head + rows + "\n2026-11-14 확인")
    assert (problems, cols, n) == ([], 5, 10)


def test_비교표의_잘못된_칸():
    head = "| 기능 | A | B | C | D | E |\n|---|---|---|---|---|---|\n"
    rows = "".join(f"| 기능{i} | 있음 | ○ | ○ | ○ | ○ |\n" for i in range(10))
    problems, _, _ = c.check_table(head + rows + "\n2026-11-14 확인")
    assert any("있음" in p for p in problems)


def test_포지셔닝_좌표_범위():
    text = "규칙\n```mermaid\nquadrantChart\n    x-axis a --> b\n    y-axis c --> d\n    A: [1.2, 0.5]\n```\n"
    problems, n = c.check_positioning(text, min_points=1)
    assert n == 1
    assert any("0~1" in p for p in problems)


def test_포지셔닝_좌표_표기():
    text = "규칙\n```mermaid\nquadrantChart\n    x-axis a --> b\n    y-axis c --> d\n    A: [0.5, 1.0]\n```\n"
    problems, _ = c.check_positioning(text, min_points=1)
    assert any("1.0" in p for p in problems)


def test_대조_기록이_빠진_출처():
    report = "- 72.1% [S1]. 8.5개월 [S2]."
    audit = "| 번호 | 출처 | 판정 |\n|---|---|---|\n| 1 | S1 | 일치 |\n"
    problems, _ = c.audit(report, audit)
    assert problems == ["출처 S2의 대조 기록이 없다"]


def test_판정_값은_세_가지():
    audit = "| 번호 | 출처 | 판정 |\n|---|---|---|\n| 1 | S1 | 맞음 |\n"
    problems, _ = c.audit("[S1]", audit)
    assert any("맞음" in p for p in problems)


@pytest.mark.skipif(
    not (KIT / "교수" / "견본_ch04").is_dir(),
    reason="학생 키트에는 교수/ 폴더가 없다(교수용 사본에서만 실행)",
)
def test_견본은_완료_기준을_통과한다(capsys):
    assert c.main(["all", str(KIT / "교수" / "견본_ch04")]) == 0
    assert "완료 기준 통과" in capsys.readouterr().out


def test_연습_초안에서_점검기가_잡는_것은_하나뿐이다():
    problems, _ = c.scan((KIT / "시연" / "AI초안_예시.md").read_text(encoding="utf-8"))
    missing = [p for p in problems if "기호가 없는 수치" in p]
    assert len(missing) == 1 and "5,000억 원" in missing[0]


def test_양식은_아직_통과하지_못한다(tmp_path):
    names = ["시장조사", "경쟁서비스_비교표", "포지셔닝", "가치제안", "출처대조"]
    for name in names:
        (tmp_path / f"{name}.md").write_text(
            (KIT / f"{name}_양식.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert c.main(["all", str(tmp_path)]) == 1
