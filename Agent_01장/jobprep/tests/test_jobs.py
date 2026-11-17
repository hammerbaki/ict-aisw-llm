"""GET /api/health, GET /api/jobs, GET /api/jobs/{id}의 테스트 (REQ-OPS-01, REQ-JOB-01~04)."""

from datetime import date

from api import jobs


def test_health_reports_ok_and_fake_mode(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["llm_fake"] is True
    assert body["jobs"] == 30


def test_list_returns_all_jobs_without_description(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 30
    assert all("description" not in item for item in items)
    for key in ("id", "title", "company", "field", "deadline", "days_left"):
        assert key in items[0]


def test_list_is_sorted_by_deadline(client):
    deadlines = [item["deadline"] for item in client.get("/api/jobs").json()]
    assert deadlines == sorted(deadlines)


def test_list_filters_by_field(client):
    items = client.get("/api/jobs", params={"field": "AI 서비스"}).json()
    assert len(items) > 0
    assert all(item["field"] == "AI 서비스" for item in items)


def test_list_filters_by_keyword(client):
    items = client.get("/api/jobs", params={"q": "청록데이터웍스"}).json()
    assert [item["company"] for item in items] == ["청록데이터웍스"]


def test_list_with_unknown_field_is_empty(client):
    assert client.get("/api/jobs", params={"field": "없는분야"}).json() == []


def test_detail_returns_one_job_with_description(client):
    response = client.get("/api/jobs/1")
    assert response.status_code == 200
    job = response.json()
    assert job["id"] == 1
    assert "[주요 업무]" in job["description"]


def test_detail_of_missing_job_is_404(client):
    assert client.get("/api/jobs/999").status_code == 404


def test_days_left_uses_today(monkeypatch):
    monkeypatch.setattr(jobs, "today", lambda: date(2027, 9, 1))
    job = {"deadline": "2027-09-08"}
    assert jobs.days_left(job) == 7
