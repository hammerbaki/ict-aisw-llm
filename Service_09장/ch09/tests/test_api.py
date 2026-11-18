"""요약 API의 동작: 정상, 입력 검사, 형식 오류, API 오류, 요청 제한, 캐시."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app as app_module
from api import llm

POSTING = (Path(__file__).resolve().parent.parent / "eval" / "공고" / "P01.txt").read_text(encoding="utf-8")


@pytest.fixture
def client():
    app_module._cache.clear()
    app_module._hits.clear()
    return TestClient(app_module.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["fake"] is True


def test_summary_fake(client):
    r = client.post("/api/summary", json={"text": POSTING})
    assert r.status_code == 200
    body = r.json()
    assert set(body["summary"]) == {"핵심업무", "자격요건", "마감일", "주의점"}
    assert body["summary"]["마감일"] == "2027-04-20"
    assert body["meta"]["fake"] is True and body["meta"]["prompt"] == "v3"


@pytest.mark.parametrize("text", ["", "짧다", "가" * 6001])
def test_rejects_bad_length(client, text):
    assert client.post("/api/summary", json={"text": text}).status_code == 422


def test_rejects_missing_field(client):
    assert client.post("/api/summary", json={}).status_code == 422


def test_bad_json_from_model_is_502(client, monkeypatch):
    def broken(*args, **kwargs):
        return llm.LLMResult("```json\n{}\n```", 10, 10, "end_turn", "test", True)
    monkeypatch.setattr(llm, "complete", broken)
    r = client.post("/api/summary", json={"text": POSTING})
    assert r.status_code == 502
    assert "형식" in r.json()["detail"]


def test_api_error_is_503_without_secret(client, monkeypatch):
    def fail(*args, **kwargs):
        raise llm.LLMError("인증 실패: 키가 없거나 잘못되었다")
    monkeypatch.setattr(llm, "complete", fail)
    r = client.post("/api/summary", json={"text": POSTING})
    assert r.status_code == 503
    assert "sk-ant" not in r.text


def test_refusal_is_502(client, monkeypatch):
    def refuse(*args, **kwargs):
        raise llm.LLMRefused("거절")
    monkeypatch.setattr(llm, "complete", refuse)
    assert client.post("/api/summary", json={"text": POSTING}).status_code == 502


def test_cache_returns_same_summary(client):
    first = client.post("/api/summary", json={"text": POSTING}).json()
    second = client.post("/api/summary", json={"text": POSTING}).json()
    assert first["summary"] == second["summary"]
    assert second["meta"]["cached"] is True


def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "2")
    codes = [client.post("/api/summary", json={"text": POSTING + str(i)}).status_code for i in range(3)]
    assert codes == [200, 200, 429]
