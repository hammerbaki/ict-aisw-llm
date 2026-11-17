from datetime import date

from dday import dday_label


def test_three_days_left():
    assert dday_label(date(2027, 3, 18), date(2027, 3, 15)) == "D-3"


def test_ten_days_left():
    assert dday_label(date(2027, 3, 25), date(2027, 3, 15)) == "D-10"
