"""관심 공고 내보내기: 공고 번호 목록을 CSV 글로 만든다 (REQ-FAV-03, REQ-FAV-04)."""

import csv
import io

from api import jobs

COLUMNS = ["id", "title", "company", "field", "deadline", "days_left"]
MAX_IDS = 30  # 공고가 30건이므로 그보다 많은 번호는 잘못된 요청으로 본다


def parse_ids(raw):
    """쉼표로 구분한 공고 번호 문자열을 중복 없는 양의 정수 목록으로 바꾼다.

    비었거나, 양의 정수가 아닌 값이 있거나, 번호가 MAX_IDS개를 넘으면 ValueError를 낸다.
    """
    if raw is None or not raw.strip():
        raise ValueError("공고 번호(ids)가 비었다")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit() or int(part) < 1:
            raise ValueError(f"공고 번호는 양의 정수여야 한다: {part!r}")
        if int(part) not in ids:
            ids.append(int(part))
    if len(ids) > MAX_IDS:
        raise ValueError(f"공고 번호는 {MAX_IDS}개까지 받는다")
    return ids


def missing_ids(ids):
    """공고 자료에 없는 번호의 목록."""
    known = {job["id"] for job in jobs.load_jobs()}
    return [job_id for job_id in ids if job_id not in known]


def export_csv(ids):
    """공고들을 마감일이 이른 순으로 CSV 글로 만든다. 엑셀이 한국어를 읽도록 BOM을 앞에 붙인다."""
    selected = [jobs.get_job(job_id) for job_id in ids]
    selected.sort(key=lambda job: job["deadline"])
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for job in selected:
        writer.writerow([job[column] for column in COLUMNS])
    return "﻿" + buffer.getvalue()
