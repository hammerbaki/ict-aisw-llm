"""POST /api/summary와 요약 구조의 테스트 (REQ-SUM-01~04)."""

import pytest

from api import llm, summary


def test_summary_has_four_parts(client, job_text):
    response = client.post("/api/summary", json={"text": job_text})
    assert response.status_code == 200
    body = response.json()
    for key in ("duties", "qualifications", "cautions"):
        assert isinstance(body[key], list)
        assert all(isinstance(item, str) for item in body[key])
    assert body["deadline"] is None or len(body["deadline"]) == 10
    assert body["prompt_version"] == "summary_v1"
    assert body["model"] == "fake"


def test_summary_reads_deadline_and_duties(client, job_text):
    job = client.get("/api/jobs/1").json()
    body = client.post("/api/summary", json={"text": job_text}).json()
    assert body["deadline"] == job["deadline"]
    assert 1 <= len(body["duties"]) <= 5
    assert any("마감" in item for item in body["cautions"])


def test_summary_without_text_field_is_422(client):
    assert client.post("/api/summary", json={}).status_code == 422


def test_summary_when_llm_fails_is_503(client, job_text, monkeypatch):
    def broken(*args, **kwargs):
        raise llm.LLMError("시험용 실패")
    monkeypatch.setattr(llm, "complete", broken)
    assert client.post("/api/summary", json={"text": job_text}).status_code == 503


def test_summary_when_reply_is_not_json_is_502(client, job_text, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *args, **kwargs: "요약할 수 없습니다")
    assert client.post("/api/summary", json={"text": job_text}).status_code == 502


def test_parse_json_ignores_text_around_object():
    data = summary.parse_json('결과입니다.\n```json\n{"a": 1}\n```')
    assert data == {"a": 1}


def test_validate_summary_keeps_at_most_five_items():
    data = {"duties": [f"업무 {n}" for n in range(8)], "qualifications": [], "cautions": [], "deadline": None}
    assert len(summary.validate_summary(data)["duties"]) == 5


@pytest.mark.parametrize("bad", [
    {"duties": "한 문장", "qualifications": [], "cautions": [], "deadline": None},
    {"duties": [], "qualifications": [], "cautions": [], "deadline": "9월 30일"},
    {"duties": [], "qualifications": [], "deadline": None},
])
def test_validate_summary_rejects_wrong_shape(bad):
    with pytest.raises(summary.SummaryError):
        summary.validate_summary(bad)
