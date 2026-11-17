"""채용 공고 마감일 알림 (교수용 예시 결과: 보강한 요구 목록 요청판, 1장 8-7절의 (다))

집필자가 (나)의 요구 12개에 13번(지난 공고만 있을 때의 출력)을 더한 요구 목록을
모두 충족하도록 작성한 예시이다. (나) 예시와 다른 곳은 main()의 출력 부분뿐이다.
실제 Claude Code의 결과는 (나)와 (다)를 새 세션에서 따로 만들므로 파일 전체가 다를 수 있다.

사용법: python dday.py <CSV 파일 경로> [--today YYYY-MM-DD]
"""
import argparse
import csv
import sys
from datetime import date, datetime

URGENT_DAYS = 3
HEADER = ["회사", "공고명", "마감일"]


def parse_date(text):
    """YYYY-MM-DD 형식의 실제 날짜이면 date를, 아니면 None을 돌려준다."""
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def load_postings(path):
    """CSV를 읽어 (줄 번호, 회사, 공고명, 마감일 문자열)의 목록을 돌려준다.

    utf-8-sig는 엑셀이 붙이는 BOM을 지운다. newline=""은 CRLF를 csv 모듈에 맡긴다.
    """
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # 머리글
        for line_no, row in enumerate(reader, start=2):
            if not row or all(not cell.strip() for cell in row):
                continue
            row = row + [""] * (3 - len(row))
            rows.append((line_no, row[0].strip(), row[1].strip(), row[2].strip()))
    return rows


def label(days):
    return "D-DAY" if days == 0 else f"D-{days}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="채용 공고 마감일 알림")
    parser.add_argument("csv_path", help="공고 CSV 파일 경로")
    parser.add_argument("--today", help="기준일 YYYY-MM-DD (없으면 오늘)")
    args = parser.parse_args(argv)

    if args.today:
        today = parse_date(args.today)
        if today is None:
            print(f"오류: --today 날짜 형식이 잘못되었습니다: {args.today}", file=sys.stderr)
            return 2
    else:
        today = date.today()

    try:
        rows = load_postings(args.csv_path)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다: {args.csv_path}", file=sys.stderr)
        return 1

    upcoming = []
    past = 0
    for line_no, company, title, deadline_text in rows:
        deadline = parse_date(deadline_text)
        if deadline is None:
            print(f"경고: {line_no}번째 줄 마감일 형식 오류 ({deadline_text})", file=sys.stderr)
            continue
        days = (deadline - today).days
        if days < 0:
            past += 1
        else:
            upcoming.append((days, company, title, deadline))

    upcoming.sort(key=lambda item: item[0])  # 같은 날 마감은 파일 순서를 유지한다

    if not upcoming:
        if past:  # 요구 13: 지난 공고만 있으면 두 줄 대신 한 줄
            print(f"표시할 공고가 없습니다. (지난 공고 {past}건)")
            return 0
        print("표시할 공고가 없습니다.")
    for days, company, title, deadline in upcoming:
        mark = "[임박]" if days <= URGENT_DAYS else "      "
        print(f"{mark} {label(days):<6} {company}  {title}  {deadline.isoformat()}")
    if past:
        print(f"지난 공고 {past}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
