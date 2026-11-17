# -*- coding: utf-8 -*-
"""질의응답 API 고정 테스트. 고치지 않는다."""
import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import ask_route
from rag import store
from rag.config import NO_ANSWER

ROOT = Path(__file__).resolve().parents[2]  # jobprep/
DOCS = ROOT / "자료"


@pytest.fixture
def client(kit_index):
    app = FastAPI()
    app.include_router(ask_route.router)
    app.dependency_overrides[ask_route.get_index] = lambda: kit_index
    return TestClient(app)


def test_자료에_있는_질문은_근거와_함께_답한다(client):
    r = client.post("/api/ask", json={"question": "자소서 한 문항에 몇 자 정도 써야 해?"})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert body["citations"][0]["heading"] == "분량과 글자 수"
    assert "[1]" in body["answer"]


def test_자료에_없는_질문은_자료에_없다고_답한다(client, monkeypatch):
    monkeypatch.setenv("RAG_MIN_SCORE", "0.99")
    r = client.post("/api/ask", json={"question": "학생식당 이번 주 메뉴 알려줘"})
    assert r.status_code == 200
    assert r.json() == {"answer": NO_ANSWER, "grounded": False, "top_score": r.json()["top_score"], "citations": []}


def test_빈_질문은_422로_거절한다(client):
    assert client.post("/api/ask", json={"question": ""}).status_code == 422


def test_이력을_함께_보낼_수_있다(client):
    history = [{"role": "user", "content": "앞 질문"}, {"role": "assistant", "content": "앞 답"}]
    r = client.post("/api/ask", json={"question": "화상 면접 볼 때 뭘 준비해야 해?", "history": history})
    assert r.status_code == 200


def test_문서에_숨은_지시는_색인에_들어가지_않는다(tmp_path):
    docs = tmp_path / "자료"
    shutil.copytree(DOCS, docs)
    shutil.copy(ROOT / "자료_실험" / "주입_공고.md", docs / "주입_공고.md")
    index = store.build_index(docs, tmp_path / "index2")
    assert index.meta["removed_comments"] >= 1
    assert not any("이전 지시" in c["text"] for c in index.chunks)
