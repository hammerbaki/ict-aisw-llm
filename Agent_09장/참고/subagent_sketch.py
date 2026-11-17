"""서브에이전트의 원리(9장 11절): 도구 하나의 처리 함수 안에서 새 에이전트 루프를 돌리고 마지막 답만 돌려준다.

부모 에이전트는 ask_researcher 도구 하나만 가진다. 그 도구가 불리면 처리 함수가 새 messages로
run_agent()를 한 번 더 돌린다(자식 에이전트, 도구 search_jobs와 read_doc). 자식의 대화 기록은
부모에게 가지 않고, 자식의 마지막 답만 tool_result로 간다. Claude Code의 서브에이전트(Agent 도구)가
별도의 컨텍스트에서 일하고 요약만 돌려주는 것과 같은 구조이다.

사용법(저장소 폴더에서, 모의 모드)
    LLM_FAKE=1 python ~/kits/Agent_09장/참고/subagent_sketch.py
"""

import json
import os
import sys

sys.path.insert(0, os.getcwd())   # 저장소 폴더의 agent_loop를 불러온다

from agent_loop.fake_model import QUESTION, FakeModel, reply, scenario, text, tool_use  # noqa: E402
from agent_loop.loop import run_agent  # noqa: E402
from agent_loop.tools import Tool  # noqa: E402

ASK_RESEARCHER = {
    "name": "ask_researcher",
    "description": (
        "채용 공고와 학과 취업 자료를 조사하는 하위 에이전트에게 질문 하나를 맡기고, 조사 결과의 요약만 받는다. "
        "공고 검색이나 자료 읽기가 여러 번 필요한 질문에 쓴다. 하위 에이전트의 중간 과정은 돌려주지 않는다."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"question": {"type": "string", "minLength": 1, "maxLength": 300,
                                    "description": "하위 에이전트에게 맡길 질문"}},
        "required": ["question"],
        "additionalProperties": False,
    },
}

children = []


def ask_researcher(args):
    child = run_agent(args["question"], scenario("normal"))   # 새 messages, 자식만의 도구
    children.append(child)
    return child.answer or f"하위 에이전트가 답하지 못하였다(종료={child.stop})."


def main():
    for stream in (sys.stdout, sys.stderr):   # Windows에서 파이프로 넘겨도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")
    parent_model = FakeModel([
        reply("tool_use", tool_use("ask_researcher", {"question": QUESTION})),
        lambda messages: reply("end_turn", text("조사 결과를 정리해 전달한다. (모의 응답)")),
    ])
    parent = run_agent("공고와 자격증 지원을 조사해 줘", parent_model,
                       tools={"ask_researcher": Tool(ASK_RESEARCHER, ask_researcher)})
    child = children[0]
    size = lambda messages: len(json.dumps(messages, ensure_ascii=False))
    print(f"[자식] 회차 {child.turns}, 도구 호출 {sum(len(t.tool_calls) for t in child.log)}회, 기록 {size(child.messages)}자")
    print(f"[부모] 회차 {parent.turns}, 도구 호출 {sum(len(t.tool_calls) for t in parent.log)}회, 기록 {size(parent.messages)}자")
    print(f"[부모가 받은 tool_result] {parent.messages[2]['content'][0]['content'][:80]}…")


if __name__ == "__main__":
    main()
