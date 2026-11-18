from pathlib import Path

import pytest

from priority import PriorityError, load_problems, main, prioritize, severity_counts

HERE = Path(__file__).resolve().parents[1]
EXAMPLE = HERE / "예시" / "문제목록_예시.csv"
TEMPLATE = HERE.parent / "문제목록_양식.md"


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_example_counts_and_order():
    problems = load_problems(EXAMPLE)
    assert severity_counts(problems) == {4: 0, 3: 5, 2: 3, 1: 3, 0: 1}
    ranked = [p["ID"] for p in prioritize(problems)]
    assert ranked[:3] == ["U-01", "U-02", "U-03"]
    assert "U-12" not in ranked          # 심각도 0은 뺀다
    assert len(ranked) == 11


def test_tie_breaks_by_severity(tmp_path):
    p = write(tmp_path, "a.csv", "ID,문제,출처,휴리스틱,심각도,빈도\nU-01,가,직접,H1,2,3\nU-02,나,직접,H1,3,2\n")
    assert [x["ID"] for x in prioritize(load_problems(p))] == ["U-02", "U-01"]


def test_severity_4_goes_first(tmp_path):
    p = write(tmp_path, "a.csv", "ID,문제,출처,휴리스틱,심각도,빈도\nU-01,가,직접,H1,3,3\nU-02,나,직접,H3,4,1\n")
    assert [x["ID"] for x in prioritize(load_problems(p))] == ["U-02", "U-01"]


def test_markdown_table(tmp_path):
    text = (
        "# 문제 목록\n\n"
        "| 번호 | 문제 | 출처 | 휴리스틱 | 심각도 | 빈도 | 점수 | 관련 요구 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| U-01 | 결과 없음에서 돌아갈 길이 없다 | AI(A-01) 재현됨 | H9, H3 | 3 | 2 | | REQ-08 |\n"
        "| U-02 | 조건을 바꿔도 검색을 눌러야 반영된다 | 직접 | H1 | 2 | 3 | | REQ-04 |\n"
        "| U-03 | 마감이 지난 공고가 같은 모양이다 | AI(A-05) 재현됨 | H1 | 2 | 3 | | (빈틈) |\n"
        "| | | | | | | | |\n"
    )
    ranked = prioritize(load_problems(write(tmp_path, "문제목록.md", text)))
    assert [(p["ID"], p["점수"]) for p in ranked] == [("U-01", 6), ("U-02", 6), ("U-03", 6)]


def test_empty_template_is_rejected():
    with pytest.raises(PriorityError, match="한 줄도"):
        load_problems(TEMPLATE)


def test_out_of_range(tmp_path):
    p = write(tmp_path, "a.csv", "ID,문제,출처,휴리스틱,심각도,빈도\nU-01,가,직접,H1,5,1\n")
    with pytest.raises(PriorityError, match="범위 밖"):
        load_problems(p)


def test_duplicate_ids(tmp_path):
    p = write(tmp_path, "a.csv", "ID,문제,출처,휴리스틱,심각도,빈도\nU-01,가,직접,H1,1,1\nU-01,나,직접,H1,1,1\n")
    with pytest.raises(PriorityError, match="겹친다"):
        load_problems(p)


def test_missing_column(tmp_path):
    p = write(tmp_path, "a.md", "| 번호 | 문제 | 심각도 |\n|---|---|---|\n| U-01 | 가 | 1 |\n")
    with pytest.raises(PriorityError, match="없는 열"):
        load_problems(p)


def test_main_exit_codes(tmp_path, capsys):
    assert main([str(EXAMPLE)]) == 0
    assert "U-01" in capsys.readouterr().out
    assert main([str(tmp_path / "없음.csv")]) == 1
