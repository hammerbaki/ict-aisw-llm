from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import jobs_api

XML = Path(__file__).with_name("응답_지어낸것.xml").read_text(encoding="utf-8")


@pytest.fixture
def api(monkeypatch):
    calls = []

    def upstream(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=XML)

    monkeypatch.setattr(jobs_api, "client", httpx.Client(transport=httpx.MockTransport(upstream)))
    monkeypatch.setattr(jobs_api, "_cache", {"at": 0.0, "jobs": None})
    monkeypatch.setenv("WORK24_KEY", "FAKE_KEY_123")
    return TestClient(jobs_api.app), calls


def test_공고를_돌려준다(api):
    c, _ = api
    body = c.get("/api/jobs").json()
    assert body["count"] == 10
    assert body["jobs"][0]["company"] == "가나다소프트"


def test_응답에_인증키와_쓰지_않는_항목이_없다(api):
    c, _ = api
    text = c.get("/api/jobs").text
    assert "FAKE_KEY_123" not in text
    assert "busino" not in text


def test_두_번째_요청은_공공_API를_다시_부르지_않는다(api):
    c, calls = api
    c.get("/api/jobs")
    assert c.get("/api/jobs").json()["cached"] is True
    assert len(calls) == 1


def test_인증키가_없으면_503(api, monkeypatch):
    c, calls = api
    monkeypatch.delenv("WORK24_KEY")
    assert c.get("/api/jobs").status_code == 503
    assert calls == []


def test_공공_API가_실패하면_502(api, monkeypatch):
    c, _ = api
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    monkeypatch.setattr(jobs_api, "client", bad)
    r = c.get("/api/jobs")
    assert r.status_code == 502
    assert "FAKE_KEY_123" not in r.text
