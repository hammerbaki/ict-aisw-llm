"""요약 본문과 질문의 길이 제한 테스트 (REQ-SUM-05, REQ-ASK-06). 2장 기준 산출물."""

import pytest

from api import llm


@pytest.fixture
def llm_must_not_be_called(monkeypatch):
    """LLM을 부르면 실패하게 만든다. 422는 LLM을 부르기 전에 나와야 한다."""
    def forbidden(*args, **kwargs):
        raise AssertionError("LLM을 부르면 안 된다")
    monkeypatch.setattr(llm, "complete", forbidden)


# REQ-SUM-05: 비었거나 공백만 있거나 4,000자를 넘으면 LLM을 부르지 않고 422
@pytest.mark.parametrize("text", ["", "   \n\t", "가" * 4001])
def test_summary_rejects_empty_or_too_long_text(client, llm_must_not_be_called, text):
    assert client.post("/api/summary", json={"text": text}).status_code == 422


# REQ-SUM-05: 4,000자는 받아들인다(경계값)
def test_summary_accepts_text_of_4000_chars(client):
    assert client.post("/api/summary", json={"text": "가" * 4000}).status_code == 200


# REQ-ASK-06: 비었거나 공백만 있거나 500자를 넘으면 검색과 LLM 호출 없이 422
@pytest.mark.parametrize("question", ["", "  ", "가" * 501])
def test_ask_rejects_empty_or_too_long_question(client, llm_must_not_be_called, question):
    assert client.post("/api/ask", json={"question": question}).status_code == 422


# REQ-ASK-06: 500자는 받아들인다(경계값)
def test_ask_accepts_question_of_500_chars(client):
    assert client.post("/api/ask", json={"question": "가" * 500}).status_code == 200
