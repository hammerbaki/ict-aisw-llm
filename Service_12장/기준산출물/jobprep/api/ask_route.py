# -*- coding: utf-8 -*-
"""취업 자료 질의응답 API: POST /api/ask. (완성되어 있음)

10장의 api/app.py에 두 줄을 더해 붙인다.
    from api.ask_route import router as ask_router
    app.include_router(ask_router)

요청  {"question": "질문", "history": [{"role": "user", "content": "..."}, ...]}
응답  {"answer": "...", "grounded": true, "top_score": 0.41, "citations": [{"n": 1, ...}]}

대화 이력은 서버가 저장하지 않는다. 화면(브라우저)이 원래 질문과 답만 모아 두었다가 함께 보낸다.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from rag import answer as rag_answer
from rag import config, store

router = APIRouter(prefix="/api", tags=["rag"])
_cache = {}


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=40)


class Citation(BaseModel):
    n: int
    source: str
    title: str
    heading: str
    score: float
    excerpt: str
    cited: bool


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    top_score: float
    citations: list[Citation]


def get_index():
    """색인을 한 번만 읽어 둔다. 색인을 다시 만들었으면 서버를 다시 시작한다."""
    key = str(config.index_dir())
    if key not in _cache:
        try:
            _cache[key] = store.load_index()
        except (FileNotFoundError, RuntimeError) as e:
            raise HTTPException(status_code=503, detail=str(e))
    return _cache[key]


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, index=Depends(get_index)):
    history = [t.model_dump() for t in req.history]
    try:
        result = rag_answer.answer(req.question.strip(), index, history=history)
    except RuntimeError as e:  # LLM_MODEL이 비어 있는 등 설정 문제
        raise HTTPException(status_code=500, detail=str(e))
    return result
