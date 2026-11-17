"""관심 공고 내보내기 API의 인수 테스트 (REQ-FAV-03, REQ-FAV-04). ISSUE-07 작업 T1.

테스트 에이전트가 구현보다 먼저 쓴다. 구현 전에는 모두 실패한다(404: 경로가 없다).
"""

import csv
import io
from datetime import date

from api import jobs

PATH = "/api/favorites/export"


def rows_of(response):
    """응답 본문(BOM으로 시작하는 CSV)을 행의 목록으로 읽는다."""
    text = response.content.decode("utf-8")
    assert text.startswith("﻿"), "엑셀이 한국어를 읽도록 BOM으로 시작해야 한다"
    return list(csv.reader(io.StringIO(text[1:])))


def test_export_returns_csv_download(client):
    response = client.get(PATH, params={"ids": "3,1"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "favorites.csv" in response.headers["content-disposition"]


def test_export_has_header_and_rows_sorted_by_deadline(client):
    rows = rows_of(client.get(PATH, params={"ids": "1,3"}))
    assert rows[0] == ["id", "title", "company", "field", "deadline", "days_left"]
    assert [row[0] for row in rows[1:]] == ["3", "1"]   # 3번(9-09)이 1번(10-10)보다 먼저 마감


def test_export_row_matches_job(client):
    job = client.get("/api/jobs/3").json()
    rows = rows_of(client.get(PATH, params={"ids": "3"}))
    assert rows[1][:5] == ["3", job["title"], job["company"], job["field"], job["deadline"]]


def test_export_days_left_uses_today(client, monkeypatch):
    monkeypatch.setattr(jobs, "today", lambda: date(2027, 9, 1))
    rows = rows_of(client.get(PATH, params={"ids": "3"}))
    assert rows[1][5] == "8"   # 2027-09-09까지 8일


def test_export_removes_duplicate_ids(client):
    rows = rows_of(client.get(PATH, params={"ids": "1,1,1"}))
    assert len(rows) == 2


def test_export_without_ids_is_422(client):
    assert client.get(PATH).status_code == 422
    assert client.get(PATH, params={"ids": ""}).status_code == 422


def test_export_with_non_integer_id_is_422(client):
    assert client.get(PATH, params={"ids": "1,abc"}).status_code == 422
    assert client.get(PATH, params={"ids": "0"}).status_code == 422


def test_export_with_too_many_ids_is_422(client):
    ids = ",".join(str(n) for n in range(1, 32))   # 31개
    assert client.get(PATH, params={"ids": ids}).status_code == 422
    ids = ",".join(str(n) for n in range(1, 31))   # 30개는 받아들인다
    assert client.get(PATH, params={"ids": ids}).status_code == 200


def test_export_with_unknown_id_is_404(client):
    response = client.get(PATH, params={"ids": "1,999"})
    assert response.status_code == 404
    assert "999" in response.json()["detail"]
