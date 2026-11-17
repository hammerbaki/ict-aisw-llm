"""채용 공고 자료(data/jobs.json)를 읽고 고르는 함수."""

import json
from datetime import date
from pathlib import Path

JOBS_FILE = Path(__file__).resolve().parent.parent / "data" / "jobs.json"

_jobs = None  # 처음 읽은 뒤 다시 쓰는 공고 목록


def today():
    """오늘 날짜를 돌려준다. 테스트에서 날짜를 고정할 때 이 함수를 바꿔 끼운다."""
    return date.today()


def load_jobs():
    """공고 목록을 읽어 돌려준다. 파일은 한 번만 읽는다."""
    global _jobs
    if _jobs is None:
        with open(JOBS_FILE, encoding="utf-8") as f:
            _jobs = json.load(f)
    return _jobs


def days_left(job):
    """마감일까지 남은 날 수. 마감일이 지났으면 음수이다."""
    deadline = date.fromisoformat(job["deadline"])
    return (deadline - today()).days


def list_jobs(field=None, q=None, closing_within=None):
    """공고 목록을 마감일이 이른 순으로 돌려준다.

    field: 직무 분야가 이 값과 같은 공고만 남긴다.
    q: 제목, 기업명, 본문에 이 낱말이 들어간 공고만 남긴다.
    closing_within: 오늘부터 이 날 수 안에 마감되는 공고만 남긴다(REQ-JOB-06). 지난 공고는 빠진다.
    목록에는 본문(description)을 빼고 남은 날 수(days_left)를 더한다.
    """
    result = []
    for job in load_jobs():
        if field and job["field"] != field:
            continue
        if q:
            haystack = job["title"] + job["company"] + job["description"]
            if q not in haystack:
                continue
        left = days_left(job)
        if closing_within is not None and not 0 <= left <= closing_within:
            continue
        item = {key: value for key, value in job.items() if key != "description"}
        item["days_left"] = left
        result.append(item)
    result.sort(key=lambda item: item["deadline"])
    return result


def get_job(job_id):
    """id가 같은 공고 하나를 돌려준다. 없으면 None이다."""
    for job in load_jobs():
        if job["id"] == job_id:
            item = dict(job)
            item["days_left"] = days_left(job)
            return item
    return None
