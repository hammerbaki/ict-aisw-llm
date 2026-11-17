#!/usr/bin/env python3
"""
채용 공고 마감일 알리미

채용 공고를 등록하고, 마감일까지 남은 날짜(D-day)를 알려 주는 프로그램입니다.

사용법:
    python job_deadline.py add "회사명" "공고명" 2027-03-20
    python job_deadline.py list
    python job_deadline.py remove 3
"""
# 교수용 예시 결과(한 줄 요청판). 「채용 공고 마감일을 알려 주는 파이썬 프로그램을 만들어줘.」
# 한 줄만 받은 코딩 도구가 흔히 내놓는 형태를 집필자가 재현한 것이다(실제 모델 출력이 아니다).
# 학생 화면의 결과는 이것과 다르다. 비교 수업에서 「AI가 스스로 정한 것」의 예로 쓴다.
import argparse
import json
import os
from datetime import date, datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")


def load_jobs():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def d_day(deadline_str):
    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    return (deadline - date.today()).days


def cmd_add(args):
    datetime.strptime(args.deadline, "%Y-%m-%d")  # 형식 확인
    jobs = load_jobs()
    new_id = max((job["id"] for job in jobs), default=0) + 1
    jobs.append({"id": new_id, "company": args.company, "title": args.title,
                 "deadline": args.deadline})
    save_jobs(jobs)
    print(f"✅ 공고가 등록되었습니다. (ID: {new_id})")


def cmd_list(args):
    jobs = load_jobs()
    if not jobs:
        print("등록된 공고가 없습니다. add 명령으로 공고를 추가해 보세요!")
        return
    jobs.sort(key=lambda job: job["deadline"])
    print(f"{'ID':<4}{'회사':<12}{'공고명':<20}{'마감일':<12}{'남은 기간'}")
    print("-" * 60)
    for job in jobs:
        days = d_day(job["deadline"])
        if days < 0:
            status = "마감됨"
        elif days == 0:
            status = "오늘 마감! 🔥"
        elif days <= 3:
            status = f"D-{days} ⚠️"
        else:
            status = f"D-{days}"
        print(f"{job['id']:<4}{job['company']:<12}{job['title']:<20}{job['deadline']:<12}{status}")


def cmd_remove(args):
    jobs = load_jobs()
    remaining = [job for job in jobs if job["id"] != args.id]
    if len(remaining) == len(jobs):
        print(f"ID {args.id}인 공고를 찾을 수 없습니다.")
        return
    save_jobs(remaining)
    print(f"🗑️  ID {args.id} 공고를 삭제했습니다.")


def main():
    parser = argparse.ArgumentParser(description="채용 공고 마감일 알리미")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="공고 추가")
    p_add.add_argument("company", help="회사명")
    p_add.add_argument("title", help="공고명")
    p_add.add_argument("deadline", help="마감일 (YYYY-MM-DD)")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="공고 목록 보기")
    p_list.set_defaults(func=cmd_list)

    p_remove = sub.add_parser("remove", help="공고 삭제")
    p_remove.add_argument("id", type=int, help="삭제할 공고 ID")
    p_remove.set_defaults(func=cmd_remove)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
