"""공고 요약: 공고 본문을 받아 정해진 구조의 JSON으로 요약한다."""

import json
import re

from api import llm

# 요약 결과가 반드시 가져야 하는 키. 값의 형식은 validate_summary()가 검사한다.
LIST_KEYS = ("duties", "qualifications", "cautions")
MAX_ITEMS = 5  # 목록 하나에 남기는 최대 항목 수
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SummaryError(Exception):
    """LLM의 응답을 요약 구조로 읽을 수 없을 때 낸다."""


def parse_json(text):
    """응답 문자열에서 첫 '{'부터 마지막 '}'까지를 JSON으로 읽는다.

    모델이 JSON 앞뒤에 설명이나 코드 블록 표시를 붙여도 읽을 수 있게 한다.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise SummaryError("응답에 JSON이 없다")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise SummaryError(f"응답의 JSON을 읽지 못하였다: {error.msg}") from error


def validate_summary(data):
    """요약 구조를 검사하고, 필요한 키만 남긴 dict를 돌려준다. 목록은 MAX_ITEMS개까지 자른다."""
    if not isinstance(data, dict):
        raise SummaryError("응답이 JSON 객체가 아니다")
    result = {}
    for key in LIST_KEYS:
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SummaryError(f"{key}는 문자열 목록이어야 한다")
        result[key] = value[:MAX_ITEMS]
    deadline = data.get("deadline")
    if deadline is not None and not (isinstance(deadline, str) and DATE_PATTERN.match(deadline)):
        raise SummaryError("deadline은 YYYY-MM-DD 형식의 문자열이거나 null이어야 한다")
    result["deadline"] = deadline
    return result


def summarize(job_text):
    """공고 본문을 요약해 dict로 돌려준다.

    돌려주는 값: duties(핵심 업무), qualifications(자격 요건), deadline(마감일),
    cautions(주의점), prompt_version(쓴 프롬프트 판본), model(쓴 모델).
    """
    version = llm.prompt_version("summary")
    system, template = llm.load_prompt(version)
    prompt = llm.fill(template, {"JOB_TEXT": job_text})
    reply = llm.complete(system, prompt, task="summary")
    result = validate_summary(parse_json(reply))
    result["prompt_version"] = version
    result["model"] = llm.model_name()
    return result
