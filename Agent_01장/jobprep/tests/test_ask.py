"""POST /api/ask의 테스트 (REQ-ASK-01~04)."""

from api import llm


def test_answer_cites_source(client):
    response = client.post("/api/ask", json={"question": "모의면접은 한 회차에 몇 명까지 참가할 수 있나요?"})
    assert response.status_code == 200
    body = response.json()
    assert "[1]" in body["answer"]
    assert body["sources"][0]["no"] == 1
    assert body["sources"][0]["source"] == "02_취업지원센터_이용안내.md"
    assert "모의면접" in body["sources"][0]["title"]


def test_question_outside_material_says_not_found(client):
    body = client.post("/api/ask", json={"question": "내일 서울 날씨는 맑을까?"}).json()
    assert body["answer"] == "자료에 없습니다."
    assert body["sources"] == []


def test_not_found_answer_from_llm_has_no_sources(client, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *args, **kwargs: "자료에 없습니다.")
    body = client.post("/api/ask", json={"question": "모의면접은 한 회차에 몇 명까지 참가할 수 있나요?"}).json()
    assert body["answer"] == "자료에 없습니다."
    assert body["sources"] == []


def test_ask_without_question_field_is_422(client):
    assert client.post("/api/ask", json={}).status_code == 422


def test_ask_when_llm_fails_is_503(client, monkeypatch):
    def broken(*args, **kwargs):
        raise llm.LLMError("시험용 실패")
    monkeypatch.setattr(llm, "complete", broken)
    response = client.post("/api/ask", json={"question": "모의면접은 한 회차에 몇 명까지 참가할 수 있나요?"})
    assert response.status_code == 503
