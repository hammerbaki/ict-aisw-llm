"""LLM 호출을 한 곳에 모은다. 나머지 코드는 이 파일의 complete()만 부른다.

10장의 api/llm.py에 12장 0-3절의 계약을 더한 판이다. 10장의 호출부(요약, 판본 비교, 도구)는
그대로 돌고, 12장의 기능은 대화 이력(messages)과 용도(purpose)를 넘길 수 있다.

환경 변수
  LLM_FAKE=1        API를 부르지 않고 모의 응답을 낸다(키가 없어도 끝까지 돈다).
  LLM_MODEL         모델 이름. 코드에 모델 이름을 박지 않는다. 비어 있으면 DEFAULT_MODEL.
  LLM_EFFORT        output_config.effort 값(low, medium, high). 빈 문자열이면 보내지 않는다.
  ANTHROPIC_API_KEY 실제 호출에서 SDK가 스스로 읽는다. 이 파일은 키를 읽지도 출력하지도 않는다.
  (12장)
  LLM_LOG_PATH      호출 기록(JSON Lines) 파일. 기본값 api/logs/llm_calls.jsonl
  JOBPREP_VARIANT   기록에 남길 변형 이름(main, form, chat 등). 기본값 main
  LLM_FAKE_LATENCY=on  모의 모드에서 응답 시간을 흉내 낸다(300ms + 출력 토큰당 4ms)
  LLM_FAKE_FAIL=1   모의 모드에서 호출 실패를 일으킨다(오류 처리 확인용)

호출 기록에는 시각, 변형, 용도, 토큰 수, 걸린 시간만 남긴다. 사용자가 입력한 글은 남기지 않는다.
모의 모드의 토큰 수는 글자 수로 어림한 값이며 실제 토큰 수와 다르다.

실제 호출 경로는 anthropic 2.8.0(API 버전 2026-10-21)의 messages.create를 쓴다.
이 버전에서는 temperature, top_p, top_k를 보내면 400 오류이므로 보내지 않는다.
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODEL = "claude-haiku-5-5"  # 2026-11 기준 가장 싼 현행 모델. 수업 직전에 공식 목록에서 다시 확인한다
ROOT = Path(__file__).resolve().parents[1]


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
    latency_ms: int = 0  # 12장: 호출에 걸린 시간


def is_fake() -> bool:
    return os.environ.get("LLM_FAKE", "") == "1"


def model_name() -> str:
    return os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODEL


def estimate_tokens(text: str) -> int:
    """모의 모드용 어림값. 실제 토큰 수가 아니다(실제 수는 count_tokens API나 응답의 usage로 잰다)."""
    return max(1, math.ceil(len(text) * 0.8))


def log_path() -> Path:
    return Path(os.environ.get("LLM_LOG_PATH") or ROOT / "api" / "logs" / "llm_calls.jsonl")


def _log(purpose: str, result: LLMResult | None, ok: bool, latency_ms: int) -> None:
    """호출 한 번을 한 줄로 남긴다(12장). 사용자 입력과 모델 출력은 남기지 않는다."""
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "variant": os.environ.get("JOBPREP_VARIANT", "main"),
        "purpose": purpose,
        "ok": ok,
        "fake": is_fake(),
        "input_tokens": result.input_tokens if result else 0,
        "output_tokens": result.output_tokens if result else 0,
        "latency_ms": latency_ms,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_request(system: str, user: str | None = None, *, messages: list[dict] | None = None,
                  max_tokens: int = 1024, json_schema: dict | None = None) -> dict:
    """Messages API 요청 본문을 만든다. 필수는 model, max_tokens, messages 셋이다.

    user 문자열 하나를 주면 사용자 메시지 하나로, messages 목록을 주면 그 목록(대화 이력)을 그대로 보낸다.
    """
    if messages is None:
        messages = [{"role": "user", "content": user or ""}]
    request: dict = {
        "model": model_name(),
        "max_tokens": max_tokens,
        "system": system,
        "messages": [dict(m) for m in messages],
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


def _fake_feedback(system: str, last: str) -> str:
    """12장 자기소개서 피드백의 모의 응답. 양식형(JSON)과 대화형(문장)을 가른다."""
    if "JSON" in system:
        return json.dumps(
            {
                "strengths": [
                    "경험을 구체적인 상황과 행동으로 서술하였다.",
                    "지원 직무와 관련된 도구 사용 경험이 드러난다.",
                ],
                "improvements": [
                    "결과를 수치나 관찰 가능한 변화로 밝히면 설득력이 커진다.",
                    "마지막 문단에서 입사 후 할 일을 지원 회사의 업무와 연결한다.",
                ],
                "rewrite": "팀 과제에서 일정표를 공유 문서로 바꾸어 마감 지연을 두 번에서 0번으로 줄였습니다.",
            },
            ensure_ascii=False,
        )
    if "예시" in last or "고쳐" in last:
        return (
            "고쳐 쓴 예시:\n"
            "- 팀 과제에서 일정표를 공유 문서로 바꾸어 마감 지연을 두 번에서 0번으로 줄였습니다.\n"
            "- 같은 방법을 입사 후 배포 일정 관리에 적용하겠습니다."
        )
    return (
        "강점:\n- 경험을 구체적인 상황과 행동으로 서술하였습니다.\n- 지원 직무와 관련된 도구 사용 경험이 드러납니다.\n"
        "보완점:\n- 결과를 수치나 관찰 가능한 변화로 밝히면 설득력이 커집니다.\n"
        "- 마지막 문단에서 입사 후 할 일을 지원 회사의 업무와 연결해 보십시오.\n"
        "고쳐 쓴 예시:\n- 팀 과제에서 일정표를 공유 문서로 바꾸어 마감 지연을 두 번에서 0번으로 줄였습니다."
    )


def complete(system: str, user: str | None = None, *, messages: list[dict] | None = None,
             purpose: str = "summary", max_tokens: int = 1024,
             json_schema: dict | None = None, fake_text: str | None = None) -> LLMResult:
    """LLM을 한 번 부른다.

    10장 방식: complete(system, user)       사용자 메시지 하나
    12장 방식: complete(system=..., messages=[...], purpose="feedback_form")
               messages는 [{"role": "user"|"assistant", "content": str}, ...]이다(대화 이력은 프로그램이 보낸다).
    """
    start = time.perf_counter()
    request = build_request(system, user, messages=messages, max_tokens=max_tokens, json_schema=json_schema)
    if is_fake():
        if os.environ.get("LLM_FAKE_FAIL") == "1":
            _log(purpose, None, False, int((time.perf_counter() - start) * 1000))
            raise LLMError("모의 모드에서 호출 실패를 일으켰다(LLM_FAKE_FAIL=1).")
        if fake_text is None:
            if purpose.startswith("feedback"):
                fake_text = _fake_feedback(system, request["messages"][-1]["content"])
            else:
                from api.fake import fake_summary  # 모의 모드에서만 쓰는 규칙 기반 요약
                fake_text = json.dumps(fake_summary(request["messages"][-1]["content"]), ensure_ascii=False)
        sent = system + "".join(m["content"] for m in request["messages"])
        out_tok = estimate_tokens(fake_text)
        if os.environ.get("LLM_FAKE_LATENCY") == "on":
            time.sleep(0.3 + 0.004 * out_tok)
        result = LLMResult(
            text=fake_text,
            input_tokens=estimate_tokens(sent),
            output_tokens=out_tok,
            stop_reason="end_turn",
            model=request["model"] + " (모의)",
            fake=True,
            request=request,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
        _log(purpose, result, True, result.latency_ms)
        return result
    try:
        result = _call_real(request)
    except (LLMError, LLMRefused):
        _log(purpose, None, False, int((time.perf_counter() - start) * 1000))
        raise
    result.latency_ms = int((time.perf_counter() - start) * 1000)
    _log(purpose, result, True, result.latency_ms)
    return result


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
