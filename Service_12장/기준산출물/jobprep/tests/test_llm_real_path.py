"""실제 호출 경로의 요청 모양과 응답 처리. 네트워크 없이 SDK 객체를 흉내 내어 확인한다."""
from types import SimpleNamespace

import pytest

from api import llm
from api.schema import SUMMARY_SCHEMA


class FakeMessages:
    def __init__(self, response):
        self.response, self.sent = response, None

    def create(self, **kwargs):
        self.sent = kwargs
        return self.response


def install(monkeypatch, response):
    import anthropic
    messages = FakeMessages(response)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: SimpleNamespace(messages=messages))
    monkeypatch.setenv("LLM_FAKE", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-not-a-key")  # 가짜 클라이언트이므로 쓰이지 않는다
    return messages


def reply(blocks, stop="end_turn"):
    return SimpleNamespace(content=blocks, stop_reason=stop, model="claude-haiku-5-5",
                           usage=SimpleNamespace(input_tokens=812, output_tokens=143))


def test_request_shape(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "claude-test-model")
    sent = install(monkeypatch, reply([SimpleNamespace(type="text", text="{}")]))
    llm.complete("시스템", "사용자", json_schema=SUMMARY_SCHEMA)
    req = sent.sent
    assert req["model"] == "claude-test-model"           # 모델은 환경 변수에서
    assert req["messages"] == [{"role": "user", "content": "사용자"}]
    assert req["system"] == "시스템"                       # system은 messages 밖
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "temperature" not in req                       # API 2026-10-21에서는 보내면 400


def test_reads_text_blocks_by_type(monkeypatch):
    blocks = [SimpleNamespace(type="thinking", thinking="", signature="s"),
              SimpleNamespace(type="text", text='{"a": 1}')]
    install(monkeypatch, reply(blocks))
    r = llm.complete("s", "u")
    assert r.text == '{"a": 1}' and r.input_tokens == 812 and r.fake is False


def test_refusal(monkeypatch):
    install(monkeypatch, reply([], stop="refusal"))
    with pytest.raises(llm.LLMRefused):
        llm.complete("s", "u")


def test_effort_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("LLM_EFFORT", "")
    sent = install(monkeypatch, reply([SimpleNamespace(type="text", text="{}")]))
    llm.complete("s", "u")
    assert "output_config" not in sent.sent


def test_missing_key_is_clear_error(monkeypatch):
    monkeypatch.setenv("LLM_FAKE", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="키가 없다"):
        llm.complete("s", "u")
