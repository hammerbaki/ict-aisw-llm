"""공고 요약 API. 실행(jobprep 폴더에서, 가상 환경을 켠 터미널):

    python -m uvicorn api.app:app --port 8000

포트는 API 8000, 웹 8100으로 고정한다(부록 A-16). 9장의 웹은 이 서버가 같은 출처에서 함께 보낸다.
모의 모드는 .env의 LLM_FAKE=1이 정한다(부록 A-15).

브라우저는 이 서버만 부른다. Claude API를 부르는 것은 이 서버이고, 키도 이 서버의 환경 변수에만 있다.
"""
from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # .env가 있으면 읽는다. 이미 설정된 환경 변수는 덮어쓰지 않는다

from api import llm  # noqa: E402  (.env를 읽은 뒤에 불러온다)
from api.prompts import load_prompt  # noqa: E402
from api.schema import SUMMARY_SCHEMA, SummaryRequest, parse_summary  # noqa: E402

app = FastAPI(title="jobprep 요약 API", version="10.0")

# 웹을 다른 출처(예: python -m http.server 8100으로 띄운 http://localhost:8100)에서 열 때만 필요하다. 같은 서버에서 열면 쓰이지 않는다
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("WEB_ORIGIN", "http://localhost:8100").split(",") if o],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_cache: dict[str, dict] = {}
_hits: dict[str, deque] = defaultdict(deque)


def rate_limited(client: str) -> bool:
    """한 접속지에서 1분에 RATE_LIMIT_PER_MIN번까지만 받는다(무제한 소비 대책, OWASP 2025년판 LLM10 / 2026년판 LLM06)."""
    limit = int(os.environ.get("RATE_LIMIT_PER_MIN", "10"))
    now = time.monotonic()
    q = _hits[client]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "fake": llm.is_fake(), "model": llm.model_name(),
            "prompt": os.environ.get("PROMPT_VERSION", "v3")}


@app.post("/api/summary")
def summary(body: SummaryRequest, request: Request) -> dict:
    client = request.client.host if request.client else "unknown"
    if rate_limited(client):
        raise HTTPException(status_code=429, detail="요청이 너무 잦다. 1분 뒤 다시 시도한다.")

    version = os.environ.get("PROMPT_VERSION", "v3")
    key = hashlib.sha256(f"{version}\n{llm.model_name()}\n{body.text}".encode()).hexdigest()
    if key in _cache:  # 같은 공고를 다시 요약하지 않는다(비용과 일관성)
        return {**_cache[key], "meta": {**_cache[key]["meta"], "cached": True}}

    prompt = load_prompt(version)
    try:
        result = llm.complete(prompt.system, prompt.render(body.text),
                              max_tokens=1024, json_schema=SUMMARY_SCHEMA)
    except llm.LLMRefused:
        raise HTTPException(status_code=502, detail="요약을 만들 수 없는 공고이다.") from None
    except llm.LLMError as e:
        raise HTTPException(status_code=503, detail=f"요약 서비스를 쓸 수 없다. {e}") from None

    parsed, reason = parse_summary(result.text)
    if parsed is None:
        raise HTTPException(status_code=502, detail=f"요약 형식이 올바르지 않다({reason}).")

    payload = {
        "summary": parsed.model_dump(),
        "meta": {"model": result.model, "fake": result.fake, "prompt": prompt.version,
                 "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                 "cached": False},
    }
    _cache[key] = payload
    return payload


WEB_DIR = ROOT / "web"
if WEB_DIR.is_dir():  # 9장의 웹을 같은 서버에서 연다(같은 출처라 CORS가 필요 없다)
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
