"""LLM 호출을 한곳에 모은 모듈.

저장소의 모든 LLM 호출은 이 모듈의 complete()를 거친다. 호출 방식을 바꾸거나
기록을 남기거나 비용을 세는 일은 이 파일 한 곳만 고치면 된다.

환경 변수
- LLM_FAKE: "1"이면 API를 부르지 않고 정해진 규칙으로 만든 모의 응답을 돌려준다.
- LLM_MODEL: 실제 호출에 쓸 모델 이름. 코드에는 모델 이름을 적지 않는다.
- ANTHROPIC_API_KEY: 실제 호출에 쓸 API 키. SDK가 이 환경 변수를 읽는다.
- PROMPT_SUMMARY, PROMPT_ASK: 쓸 프롬프트 판본(기본값 summary_v1, ask_v1).
"""

import json
import logging
import os
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
MAX_TOKENS = 2048

logger = logging.getLogger("jobprep.llm")


class LLMError(Exception):
    """LLM을 부를 수 없거나 응답을 쓸 수 없을 때 낸다."""


def is_fake():
    """모의 모드이면 True를 돌려준다. 호출할 때마다 환경 변수를 다시 읽는다."""
    return os.environ.get("LLM_FAKE", "0") == "1"


def model_name():
    """실제 호출에 쓸 모델 이름을 돌려준다. 모의 모드이면 "fake"이다."""
    if is_fake():
        return "fake"
    return os.environ.get("LLM_MODEL", "")


def prompt_version(kind):
    """기능(summary, ask)에 쓸 프롬프트 판본 이름을 돌려준다."""
    default = {"summary": "summary_v1", "ask": "ask_v1"}[kind]
    return os.environ.get("PROMPT_" + kind.upper(), default)


def load_prompt(name):
    """prompts/<name>.txt를 읽어 (시스템 프롬프트, 사용자 프롬프트 틀)을 돌려준다.

    파일은 '### system' 줄 아래에 시스템 프롬프트를, '### user' 줄 아래에
    사용자 프롬프트 틀을 둔다. 틀 안의 {{이름}} 자리는 fill()로 채운다.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise LLMError(f"프롬프트 파일이 없다: {path.name}")
    text = path.read_text(encoding="utf-8")
    if "### system" not in text or "### user" not in text:
        raise LLMError(f"프롬프트 파일 형식이 맞지 않는다: {path.name}")
    system_part, user_part = text.split("### user", 1)
    system = system_part.split("### system", 1)[1].strip()
    return system, user_part.strip()


def fill(template, values):
    """틀의 {{이름}} 자리를 values의 값으로 바꾼다. JSON 중괄호와 섞이지 않도록 format()을 쓰지 않는다."""
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def complete(system, prompt, task):
    """LLM에 한 번 묻고 응답 문자열을 돌려준다.

    task는 "summary" 또는 "ask"이다. 모의 모드에서 어떤 규칙으로 응답을 만들지 정하고,
    기록에도 남는다.
    """
    if is_fake():
        reply = fake_reply(prompt, task)
        logger.info("task=%s model=fake input_tokens=0 output_tokens=0", task)
        return reply
    return _call_anthropic(system, prompt, task)


def _call_anthropic(system, prompt, task):
    """anthropic SDK로 Messages API를 부른다."""
    model = model_name()
    if not model:
        raise LLMError("LLM_MODEL 환경 변수가 비어 있다. .env.example을 참고해 모델 이름을 정한다.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("ANTHROPIC_API_KEY 환경 변수가 없다. 키 없이 실행하려면 LLM_FAKE=1로 둔다.")

    import anthropic  # 모의 모드에서는 SDK를 불러오지 않는다

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as error:
        logger.warning("task=%s model=%s error=%s", task, model, type(error).__name__)
        raise LLMError(f"LLM 호출에 실패하였다: {type(error).__name__}") from error

    if response.stop_reason in ("refusal", "max_tokens"):
        raise LLMError(f"LLM 응답이 끝까지 오지 않았다: stop_reason={response.stop_reason}")
    text = "".join(block.text for block in response.content if block.type == "text")
    logger.info(
        "task=%s model=%s input_tokens=%d output_tokens=%d",
        task, model, response.usage.input_tokens, response.usage.output_tokens,
    )
    return text


# ---------------------------------------------------------------------------
# 모의 응답
# 같은 입력에는 언제나 같은 응답을 낸다. 프롬프트 안의 자료만 보고 규칙으로 만든다.
# ---------------------------------------------------------------------------

def fake_reply(prompt, task):
    """task에 맞는 모의 응답을 만든다."""
    if task == "summary":
        return _fake_summary(prompt)
    if task == "ask":
        return _fake_answer(prompt)
    return "모의 응답이다."


def _between(text, start, end):
    """text에서 start와 end 사이의 글을 돌려준다. 없으면 None이다."""
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.S)
    return match.group(1) if match else None


def _bullets_under(text, heading):
    """'[heading]' 줄 아래, 다음 '[' 줄 전까지의 '- ' 항목을 모은다."""
    items = []
    inside = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            inside = line == f"[{heading}]"
            continue
        if inside and line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _fake_summary(prompt):
    """공고 본문의 절 제목과 항목을 읽어 요약 JSON을 만든다."""
    job_text = _between(prompt, "<공고>", "</공고>") or prompt
    deadline = None
    match = re.search(r"마감[^\n]*?(\d{4}-\d{2}-\d{2})", job_text)
    if match:
        deadline = match.group(1)
    summary = {
        "duties": _bullets_under(job_text, "주요 업무")[:5],
        "qualifications": _bullets_under(job_text, "자격 요건")[:5],
        "deadline": deadline,
        "cautions": _bullets_under(job_text, "유의 사항")[:5],
    }
    return json.dumps(summary, ensure_ascii=False)


def _fake_answer(prompt):
    """첫째 근거의 첫 문장을 답으로 삼고 근거 번호 [1]을 붙인다."""
    evidence = _between(prompt, "<근거 1>", "</근거 1>")
    if not evidence:
        return "자료에 없습니다."
    lines = [line.strip() for line in evidence.strip().splitlines()]
    body = " ".join(line for line in lines if line and not line.startswith("#"))
    first_sentence = re.split(r"(?<=다\.)\s", body, maxsplit=1)[0]
    return f"{first_sentence} [1]"
