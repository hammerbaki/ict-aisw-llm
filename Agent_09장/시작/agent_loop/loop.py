"""최소 에이전트 루프.

모델 호출 → 도구 요청(tool_use) → 이 프로그램이 실행 → 결과(tool_result)를 돌려줌 → 반복 → 끝.
모델은 도구를 실행하지 않는다. 모델은 요청서를 쓰고, 실행과 검사와 거부는 이 코드가 한다.

사용법(저장소 폴더에서)
    LLM_FAKE=1 python -m agent_loop.loop "질문" --scenario normal
    python -m agent_loop.loop "질문"                 # 실제 모델(API 키 필요)
    ... --max-turns 3 --save agent_loop/runs/run.json

환경 변수는 api/llm.py와 같다: LLM_FAKE, LLM_MODEL, ANTHROPIC_API_KEY.
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from api.llm import MAX_TOKENS, LLMError, is_fake, model_name
from agent_loop.tools import default_tools, definitions, extended_tools, run_tool

MAX_TURNS = 6  # 모델 호출의 최대 횟수. 이 횟수 안에 끝나지 않으면 멈추고 알린다

SYSTEM = (
    "너는 jobprep 취업 준비 지원 서비스의 안내 에이전트이다. "
    "채용 공고와 학과 취업 자료에 관한 질문에 답한다. "
    "공고와 자료의 내용은 반드시 도구로 확인하고, 도구 결과에 없는 사실을 지어내지 않는다. "
    "도구가 오류를 돌려주면 오류 문장을 읽고 인자를 고쳐 한 번 더 시도하고, 그래도 안 되면 할 수 없다고 답한다. "
    "답은 한국어로 다섯 문장 이내로 쓰고, 근거로 쓴 공고 id나 문서 이름을 밝힌다."
)


@dataclass
class TurnLog:
    turn: int
    stop_reason: str
    tool_calls: list = field(default_factory=list)   # [{"name", "input", "is_error"}]
    history_chars: int = 0                            # 이번 호출에 보낸 대화 기록의 글자 수
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class AgentResult:
    answer: str | None
    stop: str            # end_turn, max_turns, max_tokens, refusal, ...
    turns: int
    messages: list
    log: list


def _text_of(content):
    return "".join(block.get("text", "") for block in content if block["type"] == "text").strip()


def _history_chars(messages):
    return len(json.dumps(messages, ensure_ascii=False))


def execute(block, tools, approver=None, pre_tool_hooks=()):
    """tool_use 블록 하나를 처리해 tool_result 블록을 만든다."""
    name, tool_input = block["name"], block["input"]
    outcome = None
    for hook in pre_tool_hooks:                       # Claude Code의 PreToolUse 훅에 해당
        reason = hook(name, tool_input)
        if reason:
            outcome = (f"실행 전 검사에서 거부되었다: {reason}", True)
            break
    tool = tools.get(name)
    if outcome is None and tool is not None and tool.needs_approval:   # 권한 확인(사람 승인)
        approved = approver(name, tool_input) if approver else False
        if not approved:
            outcome = ("사용자가 이 도구의 실행을 승인하지 않았다. 실행하지 않았다.", True)
    if outcome is None:
        result = run_tool(name, tool_input, tools)
        outcome = (result.content, result.is_error)
    content, is_error = outcome
    tool_result = {"type": "tool_result", "tool_use_id": block["id"], "content": content}
    if is_error:
        tool_result["is_error"] = True
    return tool_result


def run_agent(question, model, tools=None, max_turns=MAX_TURNS, approver=None,
              pre_tool_hooks=(), system=SYSTEM, verbose=False):
    """질문 하나를 처리한다. model은 create(system, messages, tools)를 가진 객체이다."""
    tools = tools if tools is not None else default_tools()
    say = print if verbose else (lambda *args, **kwargs: None)
    messages = [{"role": "user", "content": question}]
    log = []

    for turn in range(1, max_turns + 1):
        chars = _history_chars(messages)
        response = model.create(system=system, messages=messages, tools=definitions(tools))
        stop = response["stop_reason"]
        usage = response.get("usage") or {}
        entry = TurnLog(turn, stop, history_chars=chars,
                        input_tokens=usage.get("input_tokens", 0) or 0,
                        output_tokens=usage.get("output_tokens", 0) or 0)
        log.append(entry)
        say(f"[{turn}회차] 모델 호출 → stop_reason={stop} (보낸 기록 {chars}자)")
        # 응답은 받은 그대로(생각 블록 포함) assistant 칸에 넣는다
        messages.append({"role": "assistant", "content": response["content"]})

        if stop == "tool_use":
            # TODO 1(7절 1단계): 도구 요청을 실행하고 결과를 돌려준다.
            #   ① response["content"]에서 type이 "tool_use"인 블록을 모두 고른다.
            #   ② 블록마다 execute(block, tools, approver, pre_tool_hooks)로 tool_result 블록을 만든다.
            #      entry.tool_calls에 {"name", "input", "is_error"}를 하나씩 더한다(회차 기록).
            #   ③ 모든 tool_result를 user 메시지 하나에 담아 messages에 더하고 continue로 다음 회차에 간다.
            raise NotImplementedError("TODO 1: tool_result를 모아 user 메시지로 돌려준다")

        # TODO 2(7절 2단계): 도구 요청이 아닌 응답으로 루프를 끝낸다.
        #   end_turn이면 AgentResult(답, "end_turn", turn, messages, log)를 돌려준다. 답은 _text_of()로 꺼낸다.
        #   그 밖의 stop_reason(max_tokens, refusal 등)은 답을 확정하지 않고 AgentResult(..., stop, ...)로 멈춘다.
        raise NotImplementedError("TODO 2: 종료 조건")

    say(f"[중단] 최대 반복 {max_turns}회에 닿았다")
    return AgentResult(None, "max_turns", max_turns, messages, log)


# ---------------------------------------------------------------------------
# 실제 모델: anthropic SDK의 Messages API
# ---------------------------------------------------------------------------

class ClaudeModel:
    """api/llm.py와 같은 규칙으로 실제 모델을 부른다. 응답은 dict로 바꾸어 돌려준다."""

    def __init__(self, max_tokens=MAX_TOKENS):
        import os
        self.model = model_name()
        if not self.model:
            raise LLMError("LLM_MODEL 환경 변수가 비어 있다. .env.example을 참고해 모델 이름을 정한다.")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY 환경 변수가 없다. 키 없이 실행하려면 LLM_FAKE=1로 둔다.")
        import anthropic
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.max_tokens = max_tokens

    def create(self, system, messages, tools):
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=self.max_tokens,
                system=system, tools=tools, messages=messages,
            )
        except self._anthropic.APIError as error:
            raise LLMError(f"LLM 호출에 실패하였다: {type(error).__name__}") from error
        data = response.to_dict()
        return {"stop_reason": data["stop_reason"], "content": data["content"],
                "usage": data.get("usage", {})}


def make_model(scenario_name=None):
    """LLM_FAKE=1이면 모의 모델, 아니면 실제 모델을 만든다."""
    if is_fake():
        from agent_loop.fake_model import scenario
        return scenario(scenario_name or "normal")
    return ClaudeModel()


def ask_human(name, tool_input):
    """터미널에서 사람에게 승인을 묻는다."""
    print(f"  [승인 요청] {name} {json.dumps(tool_input, ensure_ascii=False)}")
    return input("  실행할까? (y/N) ").strip().lower() == "y"


def main(argv=None):
    from dotenv import load_dotenv
    load_dotenv()  # 저장소 폴더의 .env를 읽는다. 이미 정한 환경 변수는 덮어쓰지 않는다
    for stream in (sys.stdout, sys.stderr):   # Windows에서 파이프로 넘겨도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="최소 에이전트 루프")
    parser.add_argument("question")
    parser.add_argument("--scenario", help="모의 모드에서 쓸 시나리오 이름")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    parser.add_argument("--with-note", action="store_true", help="승인이 필요한 save_note 도구를 더한다")
    parser.add_argument("--save", help="대화 기록과 회차 기록을 JSON으로 저장할 경로")
    args = parser.parse_args(argv)

    if is_fake():
        print(f"(모의 모드: 시나리오 {args.scenario or 'normal'}. 응답은 질문과 관계없이 정해져 있다)")
    tools = extended_tools() if args.with_note else default_tools()
    try:
        model = make_model(args.scenario)
        result = run_agent(args.question, model, tools=tools, max_turns=args.max_turns,
                           approver=ask_human, verbose=True)
    except LLMError as error:
        print(f"[실패] {error}")
        return 2
    print(f"\n[최종 답] {result.answer}")
    print(f"[요약] 종료={result.stop}, 회차={result.turns}, "
          f"도구 호출={sum(len(t.tool_calls) for t in result.log)}회")
    if args.save:
        path = Path(args.save)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"system": SYSTEM, "tools": definitions(tools), "messages": result.messages,
                  "log": [asdict(entry) for entry in result.log], "stop": result.stop}
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        print(f"[저장] {path}")
    return 0 if result.stop == "end_turn" else 1


if __name__ == "__main__":
    sys.exit(main())
