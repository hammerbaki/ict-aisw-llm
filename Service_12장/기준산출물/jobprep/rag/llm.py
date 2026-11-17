# -*- coding: utf-8 -*-
"""LLM 호출. 11장의 rag/llm.py에 12장 0-3절의 계약을 더한 판이다.

12장의 측정은 모든 LLM 호출이 api/llm.py의 complete() 한 곳을 지나 호출 기록에 남는다고 전제한다.
그래서 질의응답의 호출도 complete()로 보낸다(purpose="ask"). 환경 변수의 규칙은 10장·11장과 같다.

- LLM_FAKE=1 이면 API를 부르지 않고 모의 응답을 만든다(키가 없어도 실습이 끝까지 돈다).
- 모델 이름은 코드에 적지 않고 환경 변수 LLM_MODEL로 받는다.
- 키는 jobprep/.env의 ANTHROPIC_API_KEY로만 둔다(SDK가 알아서 읽는다). 코드와 저장소에 쓰지 않는다.

모의 응답의 규칙: 프롬프트의 첫 번째 근거 블록에서 본문 첫 문장을 옮기고 [1]을 붙인다.
근거 블록이 없으면 정해진 문장을 돌려준다. 모델의 실제 답과 다르며, 흐름을 확인하는 용도다.
"""
import os
import re

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
    """system 문자열과 messages 목록을 보내고 답 문자열을 돌려준다. 호출은 api/llm.py의 complete()가 한다."""
    from api import llm  # 질의응답도 같은 호출 기록에 남긴다(12장)

    try:
        result = llm.complete(system=system, messages=messages, purpose="ask", max_tokens=max_tokens,
                              fake_text=fake_reply(messages) if llm.is_fake() else None)
    except llm.LLMError as e:  # 11장의 API는 RuntimeError를 500으로 바꾸어 알린다
        raise RuntimeError(str(e)) from None
    return result.text
