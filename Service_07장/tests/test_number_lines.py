import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import number_lines  # noqa: E402

HEAD = "# 인터뷰 기록 01\n\n- 참여자: P01\n\n## 기록\n\n"


def test_numbers_unnumbered_lines():
    lines = (HEAD + "Q: 공고는 어디서 보나?\nA: 휴대폰으로 본다.\n관찰: 즐겨찾기를 보여 주었다.\n").splitlines()
    out, added, notes = number_lines.number(lines)
    assert added == 3
    assert out[-3:] == ["L1 Q: 공고는 어디서 보나?", "L2 A: 휴대폰으로 본다.", "L3 관찰: 즐겨찾기를 보여 주었다."]
    assert notes == []


def test_keeps_existing_numbers_and_appends():
    lines = (HEAD + "L1 Q: 하나\nL2 A: 둘\nA: 셋\n").splitlines()
    out, added, _ = number_lines.number(lines)
    assert added == 1
    assert out[-1] == "L3 A: 셋"


def test_is_idempotent():
    lines = (HEAD + "L1 Q: 하나\nL2 A: 둘\n").splitlines()
    out, added, _ = number_lines.number(lines)
    assert added == 0 and out == lines


def test_refuses_insert_between_numbered_lines():
    lines = (HEAD + "L1 Q: 하나\nA: 끼워 넣은 줄\nL2 A: 둘\n").splitlines()
    with pytest.raises(ValueError, match="앞에 번호 없는 새 줄"):
        number_lines.number(lines)


def test_refuses_out_of_order_numbers():
    lines = (HEAD + "L2 Q: 하나\nL1 A: 둘\n").splitlines()
    with pytest.raises(ValueError, match="차례대로가 아니다"):
        number_lines.number(lines)


def test_notes_lines_without_speaker():
    lines = (HEAD + "Q: 하나\n그냥 적은 줄\n").splitlines()
    _, added, notes = number_lines.number(lines)
    assert added == 1 and len(notes) == 1 and "화자 표시" in notes[0]


def test_only_record_section_is_numbered():
    lines = ("## 진행 전 메모\n\nA: 이건 기록이 아니다\n\n## 기록\n\nA: 이건 기록이다\n").splitlines()
    out, added, _ = number_lines.number(lines)
    assert added == 1
    assert "A: 이건 기록이 아니다" in out
    assert "L1 A: 이건 기록이다" in out


def test_main_writes_file_and_check_mode(tmp_path, capsys):
    p = tmp_path / "인터뷰_01.md"
    p.write_text(HEAD + "Q: 하나\nA: 둘\n", encoding="utf-8")
    assert number_lines.main([str(p), "--check"]) == 1
    assert "번호 없는 줄 2개" in capsys.readouterr().out
    assert number_lines.main([str(p)]) == 0
    assert "L2 A: 둘" in p.read_text(encoding="utf-8")
    assert number_lines.main([str(p), "--check"]) == 0


def test_skips_guidance_quotes():
    body = "> 안내: 한 줄에 발화 하나" + chr(10) + "> - `Q:` 진행자의 질문" + chr(10) + "Q: 하나" + chr(10)
    out, added, notes = number_lines.number((HEAD + body).splitlines())
    assert added == 1 and notes == []


def test_writes_lf_line_endings(tmp_path):
    # Windows에서도 줄 끝이 LF여야 한다(write_text는 CRLF로 바꾼다)
    rec = tmp_path / "인터뷰_01.md"
    rec.write_bytes((HEAD + "Q: 하나\nA: 둘\n").encode("utf-8"))
    assert number_lines.main([str(rec)]) == 0
    data = rec.read_bytes()
    assert b"L2 A: " in data and b"\r\n" not in data
