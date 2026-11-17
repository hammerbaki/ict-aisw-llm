"""요약 본문의 길이 제한 테스트 (REQ-SUM-05). 3장 키트의 2장 기준 산출물."""

import pytest

from api import llm

pytestmark = pytest.mark.req(id="REQ-SUM-05")


@pytest.fixture
def llm_must_not_be_called(monkeypatch):
    """LLM을 부르면 실패하게 만든다. 422는 LLM을 부르기 전에 나와야 한다."""
    def forbidden(*args, **kwargs):
        raise AssertionError("LLM을 부르면 안 된다")
    monkeypatch.setattr(llm, "complete", forbidden)


@pytest.mark.parametrize("text", ["", "   \n\t", "가" * 4001])
def test_summary_rejects_empty_or_too_long_text(client, llm_must_not_be_called, text):
    assert client.post("/api/summary", json={"text": text}).status_code == 422


def test_summary_accepts_text_of_4000_chars(client):
    assert client.post("/api/summary", json={"text": "가" * 4000}).status_code == 200
