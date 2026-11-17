"""공고 요약의 형식(스키마). API, 채점기, 테스트가 이 파일 하나를 함께 쓴다.

- SUMMARY_SCHEMA: Claude API의 구조화 출력(output_config.format)에 보내는 JSON 스키마.
- Summary: 받은 JSON을 프로그램 쪽에서 다시 검사하는 Pydantic 모델.
  형식을 API로 강제해도 검사는 한 번 더 한다(모의 모드, 프롬프트만 쓰는 비교, 거절 응답).
"""
from __future__ import annotations

import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

FIELDS = ("핵심업무", "자격요건", "마감일", "주의점")
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
DateText = Annotated[str, StringConstraints(pattern=DATE_PATTERN)]

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "핵심업무": {"type": "array", "items": {"type": "string"},
                 "description": "공고에 적힌 주요 업무. 1~5개"},
        "자격요건": {"type": "array", "items": {"type": "string"},
                 "description": "필수 자격 요건. 우대 사항은 넣지 않는다"},
        "마감일": {"anyOf": [{"type": "string", "format": "date"}, {"type": "null"}],
                "description": "서류 접수 마감일(YYYY-MM-DD). 공고에 없거나 상시 채용이면 null"},
        "주의점": {"type": "array", "items": {"type": "string"},
                "description": "지원자가 놓치기 쉬운 조건. 공고에 적힌 것만"},
    },
    "required": list(FIELDS),
    "additionalProperties": False,
}


class Summary(BaseModel):
    """요약 한 건. 필드 이름은 한국어 그대로 쓴다(웹의 자바스크립트도 같은 이름으로 읽는다)."""

    model_config = ConfigDict(extra="forbid")

    핵심업무: list[str] = Field(min_length=1, max_length=5)
    자격요건: list[str] = Field(max_length=8)
    마감일: DateText | None  # 기본값이 없으므로 null이라도 반드시 적어야 한다
    주의점: list[str] = Field(max_length=5)


class SummaryRequest(BaseModel):
    """웹이 보내는 요청. 길이 제한은 비용 상한이기도 하다(OWASP 2025년판 LLM10 / 2026년판 LLM06)."""

    text: str = Field(min_length=20, max_length=6000)


def parse_summary(text: str) -> tuple[Summary | None, str]:
    """응답 문자열을 요약으로 읽는다. 추측하지 않는다: 전체가 JSON 객체가 아니면 실패다.

    돌려주는 값: (요약 또는 None, 실패 이유. 성공이면 빈 문자열)
    """
    try:
        data = json.loads(text.strip())
    except (json.JSONDecodeError, AttributeError):
        return None, "JSON 아님"
    if not isinstance(data, dict):
        return None, "JSON 객체 아님"
    try:
        return Summary.model_validate(data), ""
    except ValidationError as e:
        first = e.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "(전체)"
        return None, f"형식 위반: {where} {first['type']}"
