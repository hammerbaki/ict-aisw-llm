"""jobprep 백엔드의 진입점.

실행: LLM_FAKE=1 uvicorn api.main:app --reload
문서: 서버를 띄운 뒤 http://127.0.0.1:8000/docs 에서 엔드포인트를 시험할 수 있다.
"""

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # 저장소 폴더의 .env가 있으면 읽는다. 이미 정한 환경 변수는 덮어쓰지 않는다.

from api import jobs, llm  # noqa: E402  (.env를 읽은 뒤에 불러온다)
from api.ask import answer_question  # noqa: E402
from api.summary import SummaryError, summarize  # noqa: E402


def setup_logging():
    """기록을 화면에 내보낸다. 환경 변수 LOG_DIR이 있으면 그 폴더의 파일에도 남긴다.

    파일은 access.log(요청), error.log(경고와 오류), llm.log(LLM 호출)이다.
    형식은 logs/의 운영 기록 견본과 같다.
    """
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger("jobprep")
    if root.handlers:  # 다시 불러올 때 처리기가 겹치지 않게 한다
        return
    root.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)
    log_dir = os.environ.get("LOG_DIR")
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        targets = [("jobprep.access", "access.log", logging.INFO),
                   ("jobprep.llm", "llm.log", logging.INFO),
                   ("jobprep", "error.log", logging.WARNING)]
        for name, filename, level in targets:
            handler = logging.FileHandler(Path(log_dir) / filename, encoding="utf-8")
            handler.setLevel(level)
            handler.setFormatter(formatter)
            logging.getLogger(name).addHandler(handler)


setup_logging()
access_log = logging.getLogger("jobprep.access")
error_log = logging.getLogger("jobprep.api")

app = FastAPI(title="jobprep", description="취업 준비 지원 서비스 API (실습용 기준 저장소)")

# 웹(python -m http.server, 다른 포트)에서 API를 부를 수 있게 같은 컴퓨터의 주소만 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청마다 방법, 경로, 상태 코드, 걸린 시간을 한 줄로 남긴다."""
    started = time.perf_counter()
    response = await call_next(request)
    ms = int((time.perf_counter() - started) * 1000)
    access_log.info("method=%s path=%s status=%d ms=%d",
                    request.method, request.url.path, response.status_code, ms)
    return response


class SummaryRequest(BaseModel):
    text: str  # 요약할 공고 본문


class AskRequest(BaseModel):
    question: str  # 취업 자료에 묻는 질문


MAX_SUMMARY_TEXT = 4000  # REQ-SUM-05: 요약할 본문의 최대 글자 수
MAX_QUESTION = 500  # REQ-ASK-06: 질문의 최대 글자 수


def check_length(value, limit, name):
    """비었거나(공백만 있어도) limit자를 넘으면 LLM을 부르기 전에 422로 거절한다."""
    if not value.strip():
        raise HTTPException(status_code=422, detail=f"{name}이(가) 비어 있다")
    if len(value) > limit:
        raise HTTPException(status_code=422, detail=f"{name}은(는) {limit}자 이하여야 한다")


@app.get("/api/health")
def health():
    """서버가 살아 있는지와 LLM 모드를 알려 준다. 키나 모델 이외의 설정은 내보내지 않는다."""
    return {"status": "ok", "llm_fake": llm.is_fake(), "jobs": len(jobs.load_jobs())}


@app.get("/api/jobs")
def list_jobs(field: str | None = None, q: str | None = None,
              closing_within: int | None = Query(default=None, ge=0)):
    """공고 목록. field(직무 분야), q(검색어), closing_within(마감까지 남은 날 수 상한)로 고를 수 있다."""
    return jobs.list_jobs(field=field, q=q, closing_within=closing_within)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    """공고 하나의 상세. 없으면 404이다."""
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없다")
    return job


@app.post("/api/summary")
def post_summary(body: SummaryRequest):
    """공고 본문을 핵심 업무, 자격 요건, 마감일, 주의점의 JSON으로 요약한다."""
    check_length(body.text, MAX_SUMMARY_TEXT, "공고 본문")
    try:
        return summarize(body.text)
    except llm.LLMError as error:
        error_log.error("path=/api/summary status=503 error=LLMError detail=\"%s\"", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SummaryError as error:
        error_log.error("path=/api/summary status=502 error=SummaryError detail=\"%s\"", error)
        raise HTTPException(status_code=502, detail=f"요약 결과를 해석하지 못하였다: {error}") from error


@app.post("/api/ask")
def post_ask(body: AskRequest):
    """취업 자료를 근거로 답한다. 근거가 없으면 '자료에 없습니다.'로 답한다."""
    check_length(body.question, MAX_QUESTION, "질문")
    try:
        return answer_question(body.question)
    except llm.LLMError as error:
        error_log.error("path=/api/ask status=503 error=LLMError detail=\"%s\"", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
