"""모의 모델: 정해진 응답을 정해진 순서로 돌려준다.

실제 모델 대신 루프에 끼워 루프의 코드만 시험한다. API 키와 비용이 들지 않고, 같은 시나리오는
언제나 같은 결과를 낸다. 응답의 모양은 Messages API 응답(JSON)과 같다.

    {"stop_reason": "tool_use",
     "content": [{"type": "text", "text": "..."},
                 {"type": "tool_use", "id": "toolu_...", "name": "...", "input": {...}}],
     "usage": {"input_tokens": 0, "output_tokens": 0}}

시나리오의 한 칸은 응답 dict이거나, 지금까지의 messages를 받아 응답 dict를 만드는 함수이다.
함수 칸은 앞선 도구 결과를 읽어 마지막 답을 만들 때 쓴다(api/llm.py의 fake_reply와 같은 방식).
"""

import copy
import json


class FakeModelExhausted(Exception):
    """시나리오의 응답을 다 쓴 뒤에 또 불렸다. 루프가 예상보다 많이 돌았다는 뜻이다."""


def text(value):
    return {"type": "text", "text": value}


def tool_use(name, tool_input, block_id=None):
    return {"type": "tool_use", "id": block_id, "name": name, "input": tool_input}


def reply(stop_reason, *blocks):
    return {"stop_reason": stop_reason, "content": list(blocks),
            "usage": {"input_tokens": 0, "output_tokens": 0}}


class FakeModel:
    """script의 응답을 차례로 돌려준다. repeat_last=True이면 마지막 응답을 끝없이 되풀이한다."""

    def __init__(self, script, repeat_last=False):
        self.script = list(script)
        self.repeat_last = repeat_last
        self.requests = []   # 받은 요청을 그대로 남긴다(테스트가 읽는다)
        self._next_id = 1

    def create(self, system, messages, tools):
        self.requests.append({"system": system, "messages": copy.deepcopy(messages),
                              "tools": copy.deepcopy(tools)})
        if not self.script:
            raise FakeModelExhausted(f"모의 응답 {len(self.requests) - 1}개를 다 썼는데 또 불렸다.")
        item = self.script[0] if (self.repeat_last and len(self.script) == 1) else self.script.pop(0)
        response = item(messages) if callable(item) else copy.deepcopy(item)
        for block in response["content"]:
            if block["type"] == "tool_use" and not block.get("id"):
                block["id"] = f"toolu_fake_{self._next_id:02d}"
                self._next_id += 1
        return response


# ---------------------------------------------------------------------------
# 마지막 답을 도구 결과에서 만드는 함수
# ---------------------------------------------------------------------------

def _tool_results(messages):
    """messages에서 (도구 이름, 결과 문자열, is_error)를 차례로 모은다."""
    names = {}
    found = []
    for message in messages:
        if not isinstance(message["content"], list):
            continue
        for block in message["content"]:
            if block["type"] == "tool_use":
                names[block["id"]] = block["name"]
            elif block["type"] == "tool_result":
                found.append((names.get(block["tool_use_id"]), block["content"], block.get("is_error", False)))
    return found


def _final_answer(messages):
    parts = []
    for name, content, is_error in _tool_results(messages):
        if is_error:
            continue
        if name == "search_jobs":
            data = json.loads(content)
            if data["jobs"]:
                job = data["jobs"][0]
                parts.append(f"마감이 가장 이른 공고는 {job['title']}({job['company']}, 마감 {job['deadline']}, id {job['id']})이다.")
        elif name == "read_doc":
            lines = [line for line in content.splitlines() if line and not line.startswith("#")]
            body = [line for line in lines if "가상 자료" not in line]
            if body:
                parts.append(f"자료에 따르면 「{body[0][:60]}…」")
    if not parts:
        parts.append("도구 결과에서 답을 찾지 못하였다.")
    return reply("end_turn", text(" ".join(parts) + " (모의 응답)"))


# ---------------------------------------------------------------------------
# 시나리오
# ---------------------------------------------------------------------------

QUESTION = "AI 서비스 분야에서 마감이 가장 이른 공고를 알려 주고, 자격증 응시료 지원 대상도 알려 줘."


def scenario(name):
    """이름에 맞는 FakeModel을 새로 만든다. 시나리오는 한 번 쓰면 소모되므로 매번 새로 만든다."""
    if name == "normal":        # 도구 둘을 차례로 쓰고 답한다
        return FakeModel([
            reply("tool_use", text("공고부터 찾겠다."),
                  tool_use("search_jobs", {"field": "AI 서비스", "limit": 3})),
            reply("tool_use", tool_use("read_doc", {"name": "05_자격증_응시료_지원.md"})),
            _final_answer,
        ])
    if name == "parallel":      # 한 응답에 도구 요청 둘(병렬 도구 호출)
        return FakeModel([
            reply("tool_use",
                  tool_use("search_jobs", {"field": "AI 서비스", "limit": 3}),
                  tool_use("read_doc", {"name": "05_자격증_응시료_지원.md"})),
            _final_answer,
        ])
    if name == "bad_doc":       # 없는 문서 → 오류 결과를 읽고 고쳐서 다시 부른다
        return FakeModel([
            reply("tool_use", tool_use("read_doc", {"name": "자격증.md"})),
            reply("tool_use", tool_use("read_doc", {"name": "05_자격증_응시료_지원.md"})),
            _final_answer,
        ])
    if name == "bad_args":      # 스키마에 어긋난 인자 → 입력 오류 → 고쳐서 다시
        return FakeModel([
            reply("tool_use", tool_use("search_jobs", {"field": "AI", "limit": 50})),
            reply("tool_use", tool_use("search_jobs", {"field": "AI 서비스", "limit": 3})),
            _final_answer,
        ])
    if name == "escape":        # 자료 폴더 밖을 읽으려 한다 → 거부 → 포기하고 답한다
        return FakeModel([
            reply("tool_use", tool_use("read_doc", {"name": "../../.env"})),
            reply("end_turn", text("요청한 파일은 읽을 수 없다. 학과 취업 자료만 읽을 수 있다. (모의 응답)")),
        ])
    if name == "runaway":       # 끝없이 도구만 부른다 → 최대 반복 상한에 걸린다
        return FakeModel([
            reply("tool_use", tool_use("search_jobs", {"keyword": "신입"})),
        ], repeat_last=True)
    if name == "truncated":     # 출력 한도에서 잘린 응답
        return FakeModel([
            reply("max_tokens", text("공고를 찾아보겠다. 먼저 분야별로")),
        ])
    if name == "note":          # 7절: 승인이 필요한 도구를 부른다
        return FakeModel([
            reply("tool_use", tool_use("save_note", {"title": "상담_메모", "body": "AI 서비스 공고 4건 확인"})),
            reply("end_turn", text("메모 저장을 시도하였다. (모의 응답)")),
        ])
    raise KeyError(f"없는 시나리오: {name}. 있는 시나리오: {', '.join(SCENARIOS)}")


SCENARIOS = ["normal", "parallel", "bad_doc", "bad_args", "escape", "runaway", "truncated", "note"]
