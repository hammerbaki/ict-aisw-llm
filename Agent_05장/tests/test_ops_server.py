# -*- coding: utf-8 -*-
"""운영 기록 MCP 서버(mcp/ops_server.py)의 고정 테스트. 고치지 않는다.

- 모델을 부르지 않는다. MCP 파이썬 SDK의 클라이언트(Client)로 서버를 부른다.
- 기록은 logs/의 견본이 아니라 tmp_path에 만든 작은 기록을 쓴다(환경 변수 OPS_LOG_DIR).
- 마지막 테스트는 서버를 하위 프로세스로 띄워 stdio로 연결한다(Claude Code가 하는 방식).
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "mcp" / "ops_server.py"
sys.path.insert(0, str(SERVER.parent))   # mcp/에 __init__.py를 두지 않는다(SDK 이름 mcp와 겹친다)

import ops_server  # noqa: E402
from mcp import Client, StdioServerParameters  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

ACCESS = """\
2027-01-04 09:00:00 INFO jobprep.access method=GET path=/api/health status=200 ms=2
2027-01-04 09:01:00 INFO jobprep.access method=GET path=/api/jobs status=200 ms=20
2027-01-04 09:02:00 INFO jobprep.access method=GET path=/api/jobs/7 status=404 ms=5
2027-01-04 09:03:00 INFO jobprep.access method=POST path=/api/summary status=503 ms=1200
2027-01-04 09:04:00 INFO jobprep.access method=POST path=/api/summary status=503 ms=1300
2027-01-04 09:05:00 INFO jobprep.access method=POST path=/api/ask status=200 ms=7500
2027-01-05 10:00:00 INFO jobprep.access method=POST path=/api/ask status=200 ms=2500
2027-01-05 10:01:00 INFO jobprep.access method=POST path=/api/summary status=422 ms=4
"""
ERROR = """\
2027-01-04 09:03:00 WARNING jobprep.llm task=summary model=m error=RateLimitError
2027-01-04 09:03:00 ERROR jobprep.api path=/api/summary status=503 error=LLMError detail="LLM 호출에 실패하였다: RateLimitError"
2027-01-04 09:04:00 WARNING jobprep.llm task=summary model=m error=RateLimitError
2027-01-04 09:04:00 ERROR jobprep.api path=/api/summary status=503 error=LLMError detail="LLM 호출에 실패하였다: RateLimitError"
"""
LLM = """\
2027-01-04 09:05:00 INFO jobprep.llm task=ask model=m input_tokens=900 output_tokens=100
"""


@pytest.fixture
def logs(tmp_path, monkeypatch):
    (tmp_path / "access.log").write_text(ACCESS, encoding="utf-8")
    (tmp_path / "error.log").write_text(ERROR, encoding="utf-8")
    (tmp_path / "llm.log").write_text(LLM, encoding="utf-8")
    (tmp_path / "secret.txt").write_text("읽히면 안 되는 파일", encoding="utf-8")
    monkeypatch.setenv("OPS_LOG_DIR", str(tmp_path))
    return tmp_path


def call(name, args):
    """메모리 안 연결로 도구 하나를 부르고 (is_error, 글) 을 돌려준다."""
    async def run():
        async with Client(ops_server.mcp) as client:
            result = await client.call_tool(name, args)
            return result.is_error, "\n".join(c.text for c in result.content if c.type == "text")
    return asyncio.run(run())


def list_tools():
    async def run():
        async with Client(ops_server.mcp) as client:
            return (await client.list_tools()).tools
    return asyncio.run(run())


def test_도구는_넷이고_모두_읽기_전용으로_표시된다():
    tools = list_tools()
    assert sorted(t.name for t in tools) == ["error_summary", "read_log", "slow_requests", "status_counts"]
    for t in tools:
        assert t.annotations is not None and t.annotations.read_only_hint is True, t.name
        assert t.annotations.destructive_hint is False, t.name


def test_도구_설명은_두_문장_이상이고_모든_인자에_설명이_있다():
    for t in list_tools():
        assert t.description and t.description.count("다.") >= 2, f"{t.name}: 설명이 한 문장뿐이다"
        for arg, schema in t.input_schema["properties"].items():
            assert schema.get("description"), f"{t.name}.{arg}: 인자 설명이 없다"


def test_error_summary는_같은_종류의_오류를_묶어_센다(logs):
    is_error, text = call("error_summary", {"start": "2027-01-04", "end": "2027-01-05"})
    assert not is_error
    assert "ERROR 2건" in text and "WARNING 2건" in text
    assert "RateLimitError 2건" in text


def test_status_counts는_상태_코드별로_센다(logs):
    is_error, text = call("status_counts", {"start": "2027-01-04", "end": "2027-01-05"})
    assert not is_error
    data = ops_server.status_counts(start="2027-01-04", end="2027-01-05")
    assert data["합계"] == 8
    assert data["상태별"] == {"200": 4, "404": 1, "422": 1, "503": 2}
    assert data["오류_경로별"]["/api/jobs/{id}"] == {"404": 1}
    assert "503" in text


def test_slow_requests는_기준_이상만_고른다(logs):
    is_error, text = call("slow_requests", {"min_ms": 6000, "start": "2027-01-04", "end": "2027-01-05"})
    assert not is_error
    assert "1건" in text and "ms=7500" in text
    assert "ms=2500" not in text


def test_read_log는_시각_앞뒤의_줄만_보여_준다(logs):
    is_error, text = call("read_log", {"name": "access", "around": "2027-01-04 09:03", "minutes": 1})
    assert not is_error
    assert "09:02:00" in text and "09:04:00" in text
    assert "09:05:00" not in text and "2027-01-05" not in text


def test_기록_폴더_밖의_파일은_읽지_않는다(logs):
    is_error, text = call("read_log", {"name": "../secret.txt"})
    assert is_error
    with pytest.raises(ToolError):
        ops_server.read_records("../secret.txt")
    with pytest.raises(ToolError):
        ops_server.read_records("secret")
    assert "읽히면 안 되는" not in text


def test_기간_형식이_틀리거나_너무_길면_오류로_알린다(logs):
    is_error, text = call("error_summary", {"start": "1월 4일"})
    assert is_error and "YYYY-MM-DD" in text
    is_error, text = call("error_summary", {"start": "2026-01-01", "end": "2027-01-05"})
    assert is_error and "31" in text


def test_결과는_줄_수_상한을_넘지_않는다(logs):
    many = "".join(f"2027-01-04 10:{i // 60:02d}:{i % 60:02d} INFO jobprep.access method=POST "
                   f"path=/api/ask status=200 ms=9000\n" for i in range(300))
    (logs / "access.log").write_text(many, encoding="utf-8")
    is_error, text = call("slow_requests", {"start": "2027-01-04", "end": "2027-01-04"})
    assert not is_error
    assert text.count("ms=9000") <= ops_server.MAX_LINES
    assert "상한" in text


def test_stdio로_띄워_도구_목록과_호출을_확인한다(logs):
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env={**os.environ, "OPS_LOG_DIR": str(logs)},
    )

    async def run():
        async with Client(params) as client:
            names = sorted(t.name for t in (await client.list_tools()).tools)
            result = await client.call_tool("error_summary", {"start": "2027-01-04", "end": "2027-01-05"})
            return names, result.is_error, result.content[0].text

    names, is_error, text = asyncio.run(run())
    assert names == ["error_summary", "read_log", "slow_requests", "status_counts"]
    assert not is_error and "RateLimitError" in text
