"""모든 테스트는 모의 모드에서 돈다. 키가 있어도 실제 API를 부르지 않는다."""
import pytest


@pytest.fixture(autouse=True)
def fake_mode(monkeypatch):
    monkeypatch.setenv("LLM_FAKE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("PROMPT_VERSION", "v3")
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "100")
