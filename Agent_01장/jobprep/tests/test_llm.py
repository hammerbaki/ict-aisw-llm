"""api/llm.py의 테스트: 모의 모드, 프롬프트 판본, 실제 모드의 사전 점검 (REQ-OPS-02~04)."""

import json

import pytest

from api import llm


def test_fake_mode_is_on_in_tests():
    assert llm.is_fake() is True
    assert llm.model_name() == "fake"


def test_fake_summary_is_deterministic():
    prompt = "<공고>\n[주요 업무]\n- 화면을 만든다\n[유의 사항]\n- 접수 마감: 2027-10-01 18:00\n</공고>"
    first = llm.complete("시스템", prompt, task="summary")
    assert first == llm.complete("시스템", prompt, task="summary")
    data = json.loads(first)
    assert data["duties"] == ["화면을 만든다"]
    assert data["deadline"] == "2027-10-01"


def test_fake_answer_without_evidence_is_not_found():
    assert llm.complete("시스템", "근거가 없는 프롬프트", task="ask") == "자료에 없습니다."


@pytest.mark.parametrize("name", ["summary_v1", "summary_v2", "ask_v1"])
def test_prompt_files_have_system_and_user(name):
    system, user = llm.load_prompt(name)
    assert system
    assert "{{" in user


def test_prompt_version_can_be_changed(monkeypatch):
    monkeypatch.setenv("PROMPT_SUMMARY", "summary_v2")
    assert llm.prompt_version("summary") == "summary_v2"


def test_missing_prompt_file_raises():
    with pytest.raises(llm.LLMError):
        llm.load_prompt("없는_판본")


def test_real_mode_without_key_raises_before_calling(monkeypatch):
    monkeypatch.setenv("LLM_FAKE", "0")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="ANTHROPIC_API_KEY"):
        llm.complete("시스템", "질문", task="ask")


def test_real_mode_without_model_raises(monkeypatch):
    monkeypatch.setenv("LLM_FAKE", "0")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(llm.LLMError, match="LLM_MODEL"):
        llm.complete("시스템", "질문", task="ask")
