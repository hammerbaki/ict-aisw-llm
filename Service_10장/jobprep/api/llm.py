"""LLM 호출을 한 곳에 모은다. 나머지 코드는 이 파일의 complete()만 부른다.

환경 변수
  LLM_FAKE=1        API를 부르지 않고 모의 응답을 낸다(키가 없어도 끝까지 돈다).
  LLM_MODEL         모델 이름. 코드에 모델 이름을 박지 않는다. 비어 있으면 DEFAULT_MODEL.
  LLM_EFFORT        output_config.effort 값(low, medium, high). 빈 문자열이면 보내지 않는다.
  ANTHROPIC_API_KEY 실제 호출에서 SDK가 스스로 읽는다. 이 파일은 키를 읽지도 출력하지도 않는다.

실제 호출 경로는 anthropic 2.8.0(API 버전 2026-10-21)의 messages.create를 쓴다.
이 버전에서는 temperature, top_p, top_k를 보내면 400 오류이므로 보내지 않는다.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

DEFAULT_MODEL = "claude-haiku-5-5"  # 2026-11 기준 가장 싼 현행 모델. 수업 직전에 공식 목록에서 다시 확인한다


class LLMError(Exception):
    """API 호출이 실패했다(인증, 한도, 네트워크, 서버). 메시지에 키나 원문 오류를 담지 않는다."""


class LLMRefused(Exception):
    """모델이 요청을 거절했다(stop_reason == "refusal")."""


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    model: str
    fake: bool
    request: dict = field(default_factory=dict)  # 보낸 요청(키 제외). 수업에서 구조를 보기 위해 남긴다


def is_fake() -> bool:
    return os.environ.get("LLM_FAKE", "") == "1"


def model_name() -> str:
    return os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODEL


def estimate_tokens(text: str) -> int:
    """모의 모드용 어림값. 실제 토큰 수가 아니다(실제 수는 count_tokens API나 응답의 usage로 잰다)."""
    return max(1, math.ceil(len(text) * 0.8))


def build_request(system: str, user: str, *, max_tokens: int = 1024,
                  json_schema: dict | None = None) -> dict:
    """Messages API 요청 본문을 만든다. 필수는 model, max_tokens, messages 셋이다."""
    request: dict = {
        "model": model_name(),
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    output_config: dict = {}
    effort = os.environ.get("LLM_EFFORT", "low").strip()
    if effort:
        output_config["effort"] = effort
    if json_schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": json_schema}
    if output_config:
        request["output_config"] = output_config
    return request


def complete(system: str, user: str, *, max_tokens: int = 1024,
             json_schema: dict | None = None, fake_text: str | None = None) -> LLMResult:
    """한 번 묻고 한 번 받는다. 대화 이력은 없다(이력이 필요하면 messages에 직접 쌓아 보낸다)."""
    request = build_request(system, user, max_tokens=max_tokens, json_schema=json_schema)
    if is_fake():
        if fake_text is None:
            from api.fake import fake_summary  # 모의 모드에서만 쓰는 규칙 기반 요약
            fake_text = json.dumps(fake_summary(user), ensure_ascii=False)
        return LLMResult(
            text=fake_text,
            input_tokens=estimate_tokens(system + user),
            output_tokens=estimate_tokens(fake_text),
            stop_reason="end_turn",
            model=request["model"] + " (모의)",
            fake=True,
            request=request,
        )
    return _call_real(request)


def _call_real(request: dict) -> LLMResult:
    """실제 호출. 집필 시점(2026-11-14)에는 키가 없어 실행해 보지 못했고, SDK 시그니처와 공식 문서로 대조하였다."""
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("키가 없다: .env의 ANTHROPIC_API_KEY를 채우거나 LLM_FAKE=1로 실행한다")
    client = anthropic.Anthropic(max_retries=2, timeout=30.0)  # 키는 ANTHROPIC_API_KEY에서 SDK가 읽는다
    try:
        response = client.messages.create(**request)
    except anthropic.AuthenticationError:
        raise LLMError("인증 실패: 키가 없거나 잘못되었다") from None
    except anthropic.RateLimitError:
        raise LLMError("사용 한도 초과: 잠시 뒤 다시 시도한다") from None
    except anthropic.BadRequestError as e:
        raise LLMError(f"요청 형식 오류(400): {type(e).__name__}") from None
    except anthropic.APIStatusError as e:
        raise LLMError(f"API 오류: HTTP {e.status_code}") from None
    except anthropic.APIConnectionError:
        raise LLMError("네트워크 오류: API 서버에 닿지 못했다") from None

    if response.stop_reason == "refusal":
        raise LLMRefused("모델이 요청을 거절하였다")
    # 응답 content는 블록의 목록이다. thinking 블록이 앞에 올 수 있으므로 위치가 아니라 type으로 고른다
    text = "".join(block.text for block in response.content if block.type == "text")
    return LLMResult(
        text=text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        stop_reason=response.stop_reason or "",
        model=response.model,
        fake=False,
        request=request,
    )


def count_tokens(system: str, user: str) -> tuple[int, bool]:
    """입력 토큰 수. 실제 모드에서는 count_tokens API(무료, 별도 한도), 모의 모드에서는 어림값."""
    if is_fake():
        return estimate_tokens(system + user), True
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("키가 없다: .env의 ANTHROPIC_API_KEY를 채우거나 LLM_FAKE=1로 실행한다")
    client = anthropic.Anthropic()
    result = client.messages.count_tokens(
        model=model_name(),
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return result.input_tokens, False
