"""GET /api/jobs?closing_within=N의 테스트 (REQ-JOB-06). 3장 키트의 2장 기준 산출물."""

from datetime import date

import pytest

from api import jobs

pytestmark = pytest.mark.req(id="REQ-JOB-06")


@pytest.fixture
def fixed_today(monkeypatch):
    """기준일을 2027-09-01로 고정한다. 이날부터 7일 안에 마감되는 공고는 2027-09-08의 1건이다."""
    monkeypatch.setattr(jobs, "today", lambda: date(2027, 9, 1))


def test_closing_within_7_days_returns_only_jobs_due_soon(client, fixed_today):
    items = client.get("/api/jobs", params={"closing_within": 7}).json()
    assert len(items) == 1
    assert items[0]["deadline"] == "2027-09-08"
    assert all(0 <= item["days_left"] <= 7 for item in items)


def test_closing_within_excludes_past_deadlines(client, monkeypatch):
    monkeypatch.setattr(jobs, "today", lambda: date(2027, 9, 9))
    items = client.get("/api/jobs", params={"closing_within": 0}).json()
    assert [item["deadline"] for item in items] == ["2027-09-09"]
    assert all(item["days_left"] == 0 for item in items)
    assert all(item["deadline"] != "2027-09-08" for item in items)


def test_closing_within_combines_with_field(client, fixed_today):
    wide = client.get("/api/jobs", params={"closing_within": 120}).json()
    field = wide[0]["field"]
    items = client.get("/api/jobs", params={"closing_within": 120, "field": field}).json()
    assert items
    assert all(item["field"] == field and item["days_left"] <= 120 for item in items)


@pytest.mark.parametrize("value", ["-1", "abc", "1.5"])
def test_closing_within_rejects_invalid_values(client, value):
    assert client.get("/api/jobs", params={"closing_within": value}).status_code == 422
