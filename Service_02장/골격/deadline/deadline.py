"""지원 일정 목록(CSV)을 읽어 공고마다 마감까지 남은 날을 보여 준다.

사용법:
    python deadline.py                       # applications.csv, 기준일은 오늘
    python deadline.py --today 2027-03-15    # 기준일을 정해 실행
"""
import argparse
import csv
from datetime import date
from pathlib import Path

from dday import dday_label

HERE = Path(__file__).resolve().parent


def load_applications(path):
    """CSV를 읽어 공고 목록을 만든다. 열: 회사, 직무, 마감일(YYYY-MM-DD)."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = csv.DictReader(f)
        return [
            {
                "company": row["회사"],
                "position": row["직무"],
                "deadline": date.fromisoformat(row["마감일"]),
            }
            for row in rows
        ]


def render(applications, today):
    """공고 목록을 화면에 찍을 줄의 목록으로 바꾼다.

    순서는 CSV의 순서를 따른다. CSV의 순서는 사용자가 정한 지원 우선순위이다.
    """
    lines = []
    for app in applications:
        label = dday_label(app["deadline"], today)
        lines.append(f"{label:>6}  {app['deadline']}  {app['company']} · {app['position']}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="지원 일정의 마감까지 남은 날을 보여 준다.")
    parser.add_argument("csv", nargs="?", default=str(HERE / "applications.csv"),
                        help="지원 일정 CSV 파일 (기본: applications.csv)")
    parser.add_argument("--today", type=date.fromisoformat,
                        help="기준일 YYYY-MM-DD (기본: 오늘)")
    args = parser.parse_args(argv)
    today = args.today or date.today()
    for line in render(load_applications(args.csv), today):
        print(line)


if __name__ == "__main__":
    main()
