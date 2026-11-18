"""ears_check.py의 테스트. 키트 폴더에서 `python -m pytest -q`로 실행한다."""
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "도구"))

import ears_check as ec  # noqa: E402


def run(text, systems=("시스템",)):
    return ec.check_spec(text, list(systems))


def one(sentence, label=None, rid="REQ-001"):
    lab = f"[{label}] " if label else ""
    report = run(f"- **{rid}** {lab}{sentence}\n")
    return report, report.requirements[0] if report.requirements else None


@pytest.mark.parametrize("sentence,pattern", [
    ("시스템은 공고마다 마감일을 표시해야 한다.", "상시"),
    ("사용자가 상태를 고르면, 시스템은 그 상태의 공고만 표시해야 한다.", "사건"),
    ("사용자가 검색을 누를 때, 시스템은 결과를 표시해야 한다.", "사건"),
    ("요약을 만드는 동안, 시스템은 진행 표시를 보여야 한다.", "상태"),
    ("알림 기능이 포함된 경우, 시스템은 마감 하루 전에 알림을 보내야 한다.", "선택"),
    ("만약 자료 파일이 없으면, 시스템은 안내 문구를 표시해야 한다.", "원치 않는 동작"),
    ("만약 자료 파일이 없으면, 그러면 시스템은 안내 문구를 표시해야 한다.", "원치 않는 동작"),
    ("모의 모드가 켜진 동안 사용자가 요약을 요청하면, 시스템은 견본 응답을 표시해야 한다.", "복합"),
])
def test_한국어_문형_판별(sentence, pattern):
    report, req = one(sentence)
    assert req.pattern == pattern
    assert not report.errors


@pytest.mark.parametrize("sentence,pattern", [
    ("The system shall log every login attempt.", "상시"),
    ("When the user presses submit, the system shall save the form.", "사건"),
    ("While a file is uploading, the system shall show progress.", "상태"),
    ("Where the payment module is installed, the system shall show the payment menu.", "선택"),
    ("If the login fails five times, then the system shall lock the account.", "원치 않는 동작"),
    ("While the aircraft is on ground, when reverse thrust is commanded, the system shall enable it.", "복합"),
])
def test_영어_문형_판별(sentence, pattern):
    report, req = one(sentence)
    assert req.pattern == pattern
    assert not report.errors


def test_라벨과_구조가_다르면_오류():
    report, _ = one("사용자가 상태를 고르면, 시스템은 그 상태의 공고만 표시해야 한다.", label="상시")
    assert any("라벨은 [상시]인데 문장 구조는 [사건]" in f.message for f in report.errors)


def test_라벨의_다른_이름을_받는다():
    report, _ = one("시스템은 마감일을 표시해야 한다.", label="유비쿼터스")
    assert not report.errors


def test_라벨이_없으면_경고만():
    report, _ = one("시스템은 마감일을 표시해야 한다.")
    assert not report.errors
    assert any("라벨이 없다" in f.message for f in report.warnings)


def test_ID가_없는_요구_문장은_오류():
    report = run("- [사건] 사용자가 고르면, 시스템은 표시해야 한다.\n")
    assert any("ID가 없는" in f.message for f in report.errors)


def test_ID가_겹치면_오류():
    text = "- **REQ-001** 시스템은 A를 표시해야 한다.\n- **REQ-001** 시스템은 B를 표시해야 한다.\n"
    report = run(text)
    assert any("ID가 겹친다" in f.message for f in report.errors)


def test_주체가_없으면_오류():
    report, req = one("공고를 마감일 순서로 보여야 한다.")
    assert req.pattern is None
    assert any("주체가 없다" in f.message for f in report.errors)


def test_응답이_없으면_오류():
    report, _ = one("시스템은 공고를 잘 보여 준다.", rid="REQ-002")
    assert any("야 한다" in f.message for f in report.errors)


def test_한_문장에_요구가_둘이면_오류():
    report, _ = one("시스템은 공고를 저장해야 하고 알림을 보내야 한다.")
    assert any("둘 이상" in f.message for f in report.errors)


def test_조건절의_키워드가_없으면_오류():
    report, req = one("검색 결과가 많을 수 있으니, 시스템은 쪽을 나누어 표시해야 한다.")
    assert req.pattern is None
    assert any("키워드" in f.message for f in report.errors)


def test_모호한_말은_경고():
    report, _ = one("시스템은 공고를 적절히 정렬해 빠르게 표시해야 한다.")
    msgs = " ".join(f.message for f in report.warnings)
    assert "적절히" in msgs and "빠르게" in msgs


def test_잘못된은_모호한_말이_아니다():
    report, _ = one("만약 잘못된 날짜가 들어오면, 시스템은 그 행을 건너뛰어야 한다.")
    assert not report.warnings or all("잘" not in f.message for f in report.warnings)


def test_고침_표시와_근거_괄호는_무시한다():
    report, req = one("사용자가 고르면, 시스템은 표시해야 한다. (근거: P-01) ← 고침")
    assert req.pattern == "사건"
    assert not report.errors


def test_주체_이름을_바꿀_수_있다():
    report = run("- **REQ-001** 공고웹은 공고를 표시해야 한다.\n", systems=("공고웹",))
    assert report.requirements[0].pattern == "상시"
    assert not report.errors


def test_코드_블록과_표_안의_문장은_건너뛴다():
    text = "```\n- REQ-009 엉터리 문장\n```\n| REQ-010 | 시스템은 해야 한다 |\n- **REQ-001** 시스템은 표시해야 한다.\n"
    report = run(text)
    assert [r.rid for r in report.requirements] == ["REQ-001"]


def test_수용_기준이_가리키는_요구가_없으면_오류():
    text = "- **REQ-001** 시스템은 표시해야 한다.\n- **AC-001-1** 열면 보인다.\n- **AC-007-1** 고르면 보인다.\n"
    report = run(text)
    assert any("REQ-007이 명세에 없다" in f.message for f in report.errors)


def test_수용_기준이_없는_요구는_경고():
    text = "- **REQ-001** 시스템은 A를 표시해야 한다.\n- **REQ-002** 시스템은 B를 표시해야 한다.\n- **AC-001-1** 열면 A가 보인다.\n"
    report = run(text)
    assert any(f.where == "REQ-002" and "수용 기준" in f.message for f in report.warnings)


TRACE = """| 문제 | 요구 | 수용 기준 |
|---|---|---|
| P-01 | REQ-001 | AC-001-1 |
| P-09 | REQ-005 | AC-005-1 |
"""


def test_추적표의_ID가_명세에_없으면_오류():
    text = "- **REQ-001** 시스템은 A를 표시해야 한다.\n- **REQ-002** 시스템은 B를 표시해야 한다.\n- **AC-001-1** 열면 A가 보인다.\n"
    report = run(text)
    ec.check_trace(report, TRACE, problems_text="## P-01 문제\n")
    msgs = [f.message for f in report.errors]
    assert "REQ-005가 명세에 없다" in msgs
    assert "AC-005-1가 명세에 없다" in msgs
    assert "P-09가 문제 정의 파일에 없다" in msgs
    assert any(f.where == "REQ-002" and "추적표에 없다" in f.message for f in report.warnings)


@pytest.mark.parametrize("mark", ["(관찰: 카드의 마감 표시)", "(자료: closeDt)", "(정함: 타겟이 마감을 놓친다)",
                                  "(조사: 확인표 2행)", "(추측: 화면에서 보지 못함)"])
def test_4장의_근거_표시는_무시한다(mark):
    report, req = one(f"사용자가 고르면, 시스템은 표시해야 한다. {mark}")
    assert req.pattern == "사건"
    assert not report.errors


def test_다섯_문형_예는_모두_통과한다():
    text = (KIT / "연습/다섯문형_예.md").read_text(encoding="utf-8")
    report = ec.check_spec(text, ["시스템"], r"REQ-\d{2}")
    assert [r.pattern for r in report.requirements] == ["상시", "사건", "상태", "선택", "원치 않는 동작"]
    assert not report.errors


@pytest.mark.skipif(not (KIT / "교수").is_dir(), reason="교수/ 폴더가 없는 학생용 키트")
def test_견본_명세는_오류가_없다():
    spec = (KIT / "교수/명세_예시/요구사항명세서.md").read_text(encoding="utf-8")
    report = ec.check_spec(spec, ["시스템"], r"REQ-\d{2}")
    assert len(report.requirements) >= 12
    assert sum(r.pattern == "원치 않는 동작" for r in report.requirements) >= 2
    assert len(report.criteria) >= 5
    assert not report.errors


def test_교정_연습_원문은_오류가_난다():
    text = (KIT / "연습/교정연습_원문.md").read_text(encoding="utf-8")
    report = run(text)
    assert report.errors


def test_명령줄_종료_코드(tmp_path, capsys):
    good = tmp_path / "good.md"
    good.write_text("- **REQ-01** 시스템은 표시해야 한다.\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("- **REQ-01** 화면을 잘 보여 준다.\n", encoding="utf-8")
    assert ec.main([str(good)]) == 0
    assert ec.main([str(bad)]) == 1
    assert ec.main([str(tmp_path / "없음.md")]) == 2
    warn = tmp_path / "warn.md"
    warn.write_text("- **REQ-01** 시스템은 적절히 표시해야 한다.\n", encoding="utf-8")
    assert ec.main([str(warn)]) == 0
    assert ec.main([str(warn), "--strict"]) == 1
    capsys.readouterr()
