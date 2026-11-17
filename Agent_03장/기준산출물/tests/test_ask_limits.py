"""질문의 길이 제한 테스트 (REQ-ASK-06). 3장 키트의 2장 기준 산출물."""

import pytest

from api import llm

pytestmark = pytest.mark.req(id="REQ-ASK-06")


@pytest.fixture
def llm_must_not_be_called(monkeypatch):
    """LLM을 부르면 실패하게 만든다. 422는 검색과 LLM 호출 전에 나와야 한다."""
    def forbidden(*args, **kwargs):
        raise AssertionError("LLM을 부르면 안 된다")
    monkeypatch.setattr(llm, "complete", forbidden)


@pytest.mark.parametrize("question", ["", "  ", "가" * 501])
def test_ask_rejects_empty_or_too_long_question(client, llm_must_not_be_called, question):
    assert client.post("/api/ask", json={"question": question}).status_code == 422


def test_ask_accepts_question_of_500_chars(client):
    assert client.post("/api/ask", json={"question": "가" * 500}).status_code == 200
