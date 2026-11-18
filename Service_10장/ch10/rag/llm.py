# -*- coding: utf-8 -*-
"""LLM 호출. 9장의 api/llm.py와 같은 규칙을 따른다. (완성되어 있음)

- LLM_FAKE=1 이면 API를 부르지 않고 모의 응답을 만든다(키가 없어도 실습이 끝까지 돈다).
- 모델 이름은 코드에 적지 않고 환경 변수 LLM_MODEL로 받는다.
- 키는 환경 변수 ANTHROPIC_API_KEY로만 읽는다(SDK가 알아서 읽는다). 코드와 저장소에 쓰지 않는다.

모의 응답의 규칙: 프롬프트의 첫 번째 근거 블록에서 본문 첫 문장을 옮기고 [1]을 붙인다.
근거 블록이 없으면 정해진 문장을 돌려준다. 모델의 실제 답과 다르며, 흐름을 확인하는 용도다.
"""
import os
import re

_client = None
_BLOCK = re.compile(r'<근거 번호="(\d+)" 출처="[^"]*">\n(.*?)\n</근거>', re.DOTALL)


def is_fake():
    return os.environ.get("LLM_FAKE") == "1"


def fake_reply(messages):
    prompt = messages[-1]["content"]
    blocks = _BLOCK.findall(prompt)
    if not blocks:
        return "(모의 응답) 근거 블록이 없는 프롬프트이다."
    number, body = blocks[0]
    lines = [line for line in body.splitlines() if line.strip() and not line.startswith("#")]
    first = re.split(r"(?<=[.다])\s", " ".join(lines), maxsplit=1)[0] if lines else body[:80]
    return f"(모의 응답) {first} [{number}]"


def call_llm(system, messages, max_tokens=600):
    """system 문자열과 messages 목록을 보내고 답 문자열을 돌려준다."""
    if is_fake():
        return fake_reply(messages)
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise RuntimeError("LLM_MODEL 환경 변수가 비어 있다. 수업에서 안내한 모델 이름을 넣거나 LLM_FAKE=1로 실행한다")
    global _client
    if _client is None:
        import anthropic  # 모의 모드에서는 불러오지 않는다
        _client = anthropic.Anthropic()
    response = _client.messages.create(model=model, max_tokens=max_tokens, system=system, messages=messages)
    return "".join(block.text for block in response.content if block.type == "text")
