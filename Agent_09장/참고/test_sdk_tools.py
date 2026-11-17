"""Agent SDK 판(agent_loop/sdk_agent.py)의 처리 함수와 옵션을 모델 없이 시험한다.

claude-agent-sdk가 설치되어 있지 않으면 건너뛴다(9장 10절에서 설치한다).
"""

import asyncio

import pytest

pytest.importorskip("claude_agent_sdk")

from agent_loop import sdk_agent  # noqa: E402


def test_search_jobs_handler_returns_text_content():
    result = asyncio.run(sdk_agent.search_jobs_tool.handler({"field": "AI 서비스", "limit": 2}))
    assert result["content"][0]["type"] == "text"
    assert '"returned": 2' in result["content"][0]["text"]
    assert "is_error" not in result


def test_read_doc_handler_marks_error():
    result = asyncio.run(sdk_agent.read_doc_tool.handler({"name": "../../.env"}))
    assert result["is_error"] is True


def test_options_limit_the_agent():
    options = sdk_agent.build_options()
    assert options.tools == []
    assert options.allowed_tools == ["mcp__jobprep__search_jobs", "mcp__jobprep__read_doc"]
    assert options.permission_mode == "dontAsk"
    assert options.max_turns == sdk_agent.MAX_TURNS
    assert options.setting_sources == []
