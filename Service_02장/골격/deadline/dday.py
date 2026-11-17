"""마감일까지 남은 날을 D-day 표기로 바꾼다."""
from datetime import date


def dday_label(deadline: date, today: date) -> str:
    """마감일과 기준일로 D-day 표기를 만든다.

    남은 날이 n일이면 "D-n", 마감일이 지났으면 지난 날 수로 "D+n"을 돌려준다.
    """
    left = (deadline - today).days
    if left >= 0:
        return f"D-{left}"
    return f"D+{-left}"
