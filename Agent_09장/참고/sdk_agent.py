"""같은 에이전트를 Claude Agent SDK로 만든 판(9장 10절 대조용).

loop.py에서 직접 쓴 것(모델 호출, tool_use 꺼내기, tool_result 만들기, 반복, 상한)을 SDK가 맡는다.
이 파일이 쓰는 것은 도구(정의와 처리 함수)와 옵션뿐이다. 도구의 정의와 검사는 tools.py를 그대로 쓴다.

필요한 것
- pip install "claude-agent-sdk==0.2.182"  (Claude Code 실행 파일이 함께 설치된다)
- ANTHROPIC_API_KEY(.env), LLM_MODEL. Agent SDK는 API 키로 인증한다. Claude.ai 로그인을 쓰지 않는다.
- 모의 모드가 없다. 처리 함수는 tests/test_sdk_tools.py가 모델 없이 시험한다.

사용법(저장소 폴더에서)
    python -m agent_loop.sdk_agent "질문"
"""

import asyncio
import os
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from agent_loop.loop import MAX_TURNS, SYSTEM
from agent_loop.tools import READ_DOC, REPO_DIR, SEARCH_JOBS, default_tools, run_tool

TOOLS = default_tools()


def to_sdk_result(outcome):
    """tools.py의 ToolOutcome을 SDK 처리 함수의 반환 형식으로 바꾼다."""
    result = {"content": [{"type": "text", "text": outcome.content}]}
    if outcome.is_error:
        result["is_error"] = True
    return result


@tool(SEARCH_JOBS["name"], SEARCH_JOBS["description"], SEARCH_JOBS["input_schema"])
async def search_jobs_tool(args):
    return to_sdk_result(run_tool("search_jobs", args, TOOLS))


@tool(READ_DOC["name"], READ_DOC["description"], READ_DOC["input_schema"])
async def read_doc_tool(args):
    return to_sdk_result(run_tool("read_doc", args, TOOLS))


async def log_tool_request(input_data, tool_use_id, context):
    """PreToolUse 훅: 도구가 실행되기 직전에 불린다. 빈 dict를 돌려주면 그대로 진행한다."""
    print(f"  [훅 PreToolUse] {input_data['tool_name']} {input_data['tool_input']}")
    return {}


def build_options():
    server = create_sdk_mcp_server(name="jobprep", version="1.0.0", tools=[search_jobs_tool, read_doc_tool])
    return ClaudeAgentOptions(
        model=os.environ.get("LLM_MODEL") or None,
        system_prompt=SYSTEM,
        mcp_servers={"jobprep": server},
        tools=[],                                   # 내장 도구(Read, Bash 등)를 모두 뺀다
        allowed_tools=["mcp__jobprep__search_jobs", "mcp__jobprep__read_doc"],
        permission_mode="dontAsk",                  # 허용 목록 밖의 호출은 묻지 않고 거부한다
        setting_sources=[],                         # CLAUDE.md, settings.json을 읽지 않는다
        max_turns=MAX_TURNS,                        # loop.py의 MAX_TURNS와 같은 상한
        max_budget_usd=0.05,                        # 비용 상한(추정치로 판정하므로 여유를 둔다)
        cwd=str(REPO_DIR),
        hooks={"PreToolUse": [HookMatcher(matcher="mcp__jobprep__.*", hooks=[log_tool_request])]},
    )


async def main(question):
    async for message in query(prompt=question, options=build_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"[도구 요청] {block.name} {block.input}")
                elif isinstance(block, TextBlock):
                    print(f"[모델] {block.text}")
        elif isinstance(message, ResultMessage):
            print(f"[결과] subtype={message.subtype}, 회차={message.num_turns}, 비용(USD)={message.total_cost_usd}")
            if message.subtype == "success":
                print(f"[최종 답] {message.result}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    for stream in (sys.stdout, sys.stderr):   # Windows에서 파이프로 넘겨도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    if os.environ.get("LLM_FAKE") == "1" or not os.environ.get("ANTHROPIC_API_KEY"):
        print("Agent SDK 예제는 실제 모델로만 돈다. LLM_FAKE=0과 ANTHROPIC_API_KEY(.env)가 필요하다.")
        sys.exit(2)
    try:
        asyncio.run(main(sys.argv[1]))
    except Exception as error:  # 한도에 닿으면 query()가 결과 메시지를 낸 뒤 예외를 올린다
        print(f"[종료] {type(error).__name__}: {error}")
        sys.exit(1)
