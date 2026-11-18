import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_trace  # noqa: E402
from recordfmt import RecordFormatError, load_record  # noqa: E402

RECORD = """# 인터뷰 기록 01

- 참여자: P01

## 기록

L1 Q: 요즘 공고는 어디서 보나?
L2 A: 휴대폰으로 세 군데를 따로 본다.
L3 관찰: 휴대폰을 꺼내 즐겨찾기 목록을 보여 주었다.
L4 메모: 정보가 흩어진 것이 불편한 듯하다.
L5 A: 마감일을 놓친 적이 두 번 있다.

## 진행 후 메모

- 다음에는 마감 관리를 더 묻는다.
"""


@pytest.fixture
def records(tmp_path):
    d = tmp_path / "기록"
    d.mkdir()
    (d / "인터뷰_01.md").write_text(RECORD, encoding="utf-8")
    return d


def write(tmp_path, text):
    p = tmp_path / "페르소나.md"
    p.write_text(text, encoding="utf-8")
    return p


def run(tmp_path, records, text, *extra):
    target = write(tmp_path, text)
    return check_trace.main([str(target), "--records", str(records), *extra])


def test_load_record_reads_numbered_lines(records):
    entries = load_record(records / "인터뷰_01.md")
    assert sorted(entries) == [1, 2, 3, 4, 5]
    assert entries[2] == ("A", "휴대폰으로 세 군데를 따로 본다.")


def test_valid_citations_pass(tmp_path, records, capsys):
    text = "# 페르소나\n\n## 행동\n\n- 공고를 여러 곳에서 따로 본다 [인터뷰_01:L2][인터뷰_01:L3]\n- 마감을 놓친 적이 있다 [인터뷰_01:L5]\n"
    assert run(tmp_path, records, text) == 0
    out = capsys.readouterr().out
    assert "결과: 통과" in out
    assert "인터뷰_01 3회" in out


def test_missing_line_fails(tmp_path, records, capsys):
    text = "## 행동\n\n- 밤에 공고를 몰아서 본다 [인터뷰_01:L12]\n"
    assert run(tmp_path, records, text) == 1
    out = capsys.readouterr().out
    assert "[실패]" in out and "L12이 없다" in out and "마지막 줄 L5" in out


def test_missing_record_file_fails(tmp_path, records, capsys):
    text = "## 행동\n\n- 선배에게 묻는다 [인터뷰_02:L3]\n"
    assert run(tmp_path, records, text) == 1
    assert "인터뷰_02.md가 없다" in capsys.readouterr().out


def test_range_citation(tmp_path, records, capsys):
    text = "## 행동\n\n- 흩어진 공고를 본다 [인터뷰_01:L2-L3]\n- 같은 뜻 [인터뷰_01:L2-3]\n"
    assert run(tmp_path, records, text) == 0
    text_bad = "## 행동\n\n- 범위가 기록 밖 [인터뷰_01:L4-L9]\n"
    assert run(tmp_path, records, text_bad) == 1
    assert "L6" in capsys.readouterr().out


def test_question_and_memo_citation_warns(tmp_path, records, capsys):
    text = "## 행동\n\n- 공고를 휴대폰으로 본다 [인터뷰_01:L1]\n- 불편해한다 [인터뷰_01:L4]\n"
    assert run(tmp_path, records, text) == 0  # 경고는 통과를 막지 않는다
    out = capsys.readouterr().out
    assert "진행자의 질문(Q)" in out
    assert "진행자의 해석(메모)" in out


def test_uncited_claim_is_missing(tmp_path, records, capsys):
    text = "## 행동\n\n- 아르바이트를 주 3회 한다\n- 졸업 후 서울에서 일하고 싶다 (가정)\n"
    assert run(tmp_path, records, text) == 1
    out = capsys.readouterr().out
    assert "[누락]" in out and "아르바이트" in out
    assert "서울" not in out


def test_front_matter_and_excluded_section_not_checked(tmp_path, records):
    text = ("# 페르소나\n\n- 근거 기록: 인터뷰_01\n\n## 작성 정보\n\n- 작성일: 2027-04-08\n\n"
            "## 행동\n\n- 마감을 놓친다 [인터뷰_01:L5]\n")
    assert run(tmp_path, records, text) == 0


def test_table_rows_need_citation(tmp_path, records, capsys):
    text = ("## 공감 지도\n\n| 영역 | 내용 |\n|---|---|\n| 말한다 | 세 군데를 따로 본다 [인터뷰_01:L2] |\n"
            "| 느낀다 | 막막하다 |\n| 생각한다 | |\n")
    assert run(tmp_path, records, text) == 1
    out = capsys.readouterr().out
    assert "막막하다" in out
    assert out.count("[누락]") == 1


def test_malformed_citation_fails(tmp_path, records, capsys):
    text = "## 행동\n\n- 공고를 따로 본다 [인터뷰_01:L2,L3]\n"
    assert run(tmp_path, records, text) == 1
    assert "형식이 틀렸다" in capsys.readouterr().out


def test_five_line_range_does_not_warn(tmp_path, records, capsys):
    text = "## 행동\n\n- 전부 [인터뷰_01:L1-L5]\n"
    run(tmp_path, records, text)
    assert "범위가" not in capsys.readouterr().out  # 5줄은 경고하지 않는다


def test_report_written(tmp_path, records):
    report = tmp_path / "대조표.md"
    text = "## 행동\n\n- 마감을 놓친다 [인터뷰_01:L5]\n"
    assert run(tmp_path, records, text, "--report", str(report)) == 0
    body = report.read_text(encoding="utf-8")
    assert "| 인터뷰_01:L5 | A | 마감일을 놓친 적이 두 번 있다. |" in body


def test_duplicate_number_is_format_error(tmp_path):
    p = tmp_path / "인터뷰_09.md"
    p.write_text("## 기록\n\nL1 A: 하나\nL1 A: 둘\n", encoding="utf-8")
    with pytest.raises(RecordFormatError):
        load_record(p)


def test_record_without_section_is_error(tmp_path):
    p = tmp_path / "인터뷰_08.md"
    p.write_text("# 기록\n\nL1 A: 제목이 틀렸다\n", encoding="utf-8")
    with pytest.raises(RecordFormatError):
        load_record(p)


def test_decision_mark_and_review_section_exempt(tmp_path, records):
    text = ("## 문제 1\n\n- HMW: 마감을 놓치지 않게 하려면? [인터뷰_01:L5]\n"
            "- 범위 밖: 자기소개서 대필은 다루지 않는다 (결정)\n\n"
            "## 검토 기록\n\n- Claude Code 초안에서 군집 하나를 나누었다\n")
    assert run(tmp_path, records, text) == 0


def test_report_uses_lf_line_endings(tmp_path, records):
    # Windows에서도 대조표의 줄 끝이 LF여야 한다(write_text는 CRLF로 바꾼다)
    report = tmp_path / "대조표.md"
    text = "## 행동\n\n- 마감을 놓친다 [인터뷰_01:L5]\n"
    assert run(tmp_path, records, text, "--report", str(report)) == 0
    assert b"\r\n" not in report.read_bytes()
