"""sus.py의 테스트. 공개된 예시 값과 경계 값으로 계산을 검산한다."""
from pathlib import Path

import pytest

from sus import SusError, load, report, summarize, sus_score

EXAMPLE = Path(__file__).resolve().parents[1] / "예시" / "sus_예시.csv"


def test_all_neutral_is_50():
    # 모든 문항에 3(보통)을 고르면 문항마다 2점, 합 20, 20 x 2.5 = 50
    assert sus_score([3] * 10) == 50.0


def test_best_and_worst():
    best = [5, 1] * 5    # 홀수 문항 5, 짝수 문항 1
    worst = [1, 5] * 5   # 홀수 문항 1, 짝수 문항 5
    assert sus_score(best) == 100.0
    assert sus_score(worst) == 0.0


def test_published_example_77_5():
    # Adobe XD Ideas(Smyk, 2020)의 예: 홀수 4,5,3,4,3 / 짝수 2,1,3,1,1 -> (14 + 17) x 2.5 = 77.5
    responses = [4, 2, 5, 1, 3, 3, 4, 1, 3, 1]
    assert sus_score(responses) == 77.5


def test_wrong_count():
    with pytest.raises(SusError, match="10개"):
        sus_score([3] * 9)


@pytest.mark.parametrize("bad", [0, 6, "3", 3.0, True])
def test_out_of_range_or_wrong_type(bad):
    responses = [3] * 10
    responses[4] = bad
    with pytest.raises(SusError, match="Q5"):
        sus_score(responses)


def test_load_example_and_scores():
    rows = load(EXAMPLE)
    assert [name for name, _ in rows] == ["P1", "P2", "P3"]
    assert [sus_score(v) for _, v in rows] == [65.0, 35.0, 75.0]


def test_summary_and_report():
    rows = load(EXAMPLE)
    s = summarize([sus_score(v) for _, v in rows])
    assert s["n"] == 3 and round(s["mean"], 2) == 58.33
    text = report(rows)
    assert "평균 58.3점" in text and "아래" in text and "5명 미만" in text


def test_load_rejects_blank_answer(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("참가자,Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8,Q9,Q10\nP9,3,3,,3,3,3,3,3,3,3\n", encoding="utf-8")
    with pytest.raises(SusError, match="P9의 Q3"):
        load(bad)


def test_load_rejects_missing_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("참가자,Q1,Q2\nP1,3,3\n", encoding="utf-8")
    with pytest.raises(SusError, match="머리글"):
        load(bad)
