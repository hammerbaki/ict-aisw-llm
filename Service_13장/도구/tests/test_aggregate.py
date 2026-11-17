"""aggregate.py의 테스트."""
from pathlib import Path

import pytest

from aggregate import (AggregateError, load_problems, load_tasks, prioritize,
                       report_tasks, severity_counts, summarize_tasks)

HERE = Path(__file__).resolve().parents[1] / "예시"


def test_task_summary_example():
    summary = summarize_tasks(load_tasks(HERE / "과업기록_예시.csv"))
    t1, t2, t3 = summary
    assert t1["levels"] == {"완전성공": 2, "사소한문제": 1, "큰문제": 0, "실패": 0}
    assert t1["완료율"] == 1.0 and round(t1["완전성공률"], 3) == 0.667
    assert t1["시간_중앙값"] == 110
    # T2: 큰문제 2, 실패 1 -> 완료율 2/3, 시간은 완료한 두 시도(160, 180)의 중앙값
    assert t2["levels"]["실패"] == 1 and t2["시간_중앙값"] == 170
    assert t2["완전성공률"] == 0.0
    assert round(t3["오류_평균"], 2) == 1.0


def test_failed_attempts_are_excluded_from_time(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("참가자,과업,결과,시간초,오류수\nP1,T9,실패,300,4\nP2,T9,실패,280,2\n", encoding="utf-8")
    (s,) = summarize_tasks(load_tasks(f))
    assert s["시간_중앙값"] is None and s["완료율"] == 0.0
    assert "-" in report_tasks([s])


def test_unknown_level_is_rejected(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("참가자,과업,결과,시간초,오류수\nP1,T1,성공,30,0\n", encoding="utf-8")
    with pytest.raises(AggregateError, match="완전성공"):
        load_tasks(f)


def test_severity_counts_and_priority():
    problems = load_problems(HERE / "문제목록_예시.csv")
    assert severity_counts(problems) == {4: 0, 3: 5, 2: 3, 1: 3, 0: 1}
    ranked = prioritize(problems)
    assert [p["ID"] for p in ranked[:3]] == ["U-01", "U-02", "U-03"]
    assert all(p["심각도"] > 0 for p in ranked)       # 심각도 0은 목록에서 빠진다
    assert len(ranked) == 11


def test_tie_breaks_by_severity(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(
        "ID,문제,출처,휴리스틱,심각도,빈도\n"
        "A,가,테스트,H1,2,3\n"
        "B,나,테스트,H1,3,2\n",
        encoding="utf-8",
    )
    ranked = prioritize(load_problems(f))
    assert [p["ID"] for p in ranked] == ["B", "A"]     # 점수 6으로 같으면 심각도 3이 앞선다


def test_severity_4_goes_first(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(
        "ID,문제,출처,휴리스틱,심각도,빈도\n"
        "A,자주 보이는 불편,테스트,H8,3,3\n"
        "B,드물지만 자료가 사라짐,휴리스틱,H3,4,1\n",
        encoding="utf-8",
    )
    ranked = prioritize(load_problems(f))
    assert [p["ID"] for p in ranked] == ["B", "A"]     # 점수는 4 < 9이지만 심각도 4가 맨 앞


def test_severity_out_of_range(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("ID,문제,출처,휴리스틱,심각도,빈도\nA,가,테스트,H1,5,1\n", encoding="utf-8")
    with pytest.raises(AggregateError, match="0~4"):
        load_problems(f)


def test_duplicate_ids(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("ID,문제,출처,휴리스틱,심각도,빈도\nA,가,테스트,H1,2,1\nA,나,테스트,H2,1,1\n", encoding="utf-8")
    with pytest.raises(AggregateError, match="겹친다"):
        load_problems(f)
