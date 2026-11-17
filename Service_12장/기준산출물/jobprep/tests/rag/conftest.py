# -*- coding: utf-8 -*-
"""RAG 테스트의 공통 준비. 고치지 않는다.

- jobprep/ 폴더를 임포트 경로에 넣는다(rag, api 패키지를 찾기 위해).
- 모든 테스트는 대체 임베딩(EMBED_BACKEND=fallback)과 모의 LLM(LLM_FAKE=1)으로 돈다.
  Ollama와 API 키가 없어도 통과해야 한다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]  # jobprep/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag import embedder, store  # noqa: E402

DOCS = ROOT / "자료"


@pytest.fixture(autouse=True)
def offline_env(monkeypatch, tmp_path):
    for name in ("CHUNK_MODE", "CHUNK_MAX_CHARS", "CHUNK_OVERLAP", "CHUNK_ADD_TITLE", "TOP_K",
                 "SEARCH_METHOD", "RAG_MIN_SCORE", "MAX_TURNS", "MAX_CONTEXT_CHARS", "DOCS_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EMBED_BACKEND", "fallback")
    monkeypatch.setenv("LLM_FAKE", "1")
    monkeypatch.setenv("INDEX_DIR", str(tmp_path / "index"))
    embedder.reset()
    yield
    embedder.reset()


@pytest.fixture
def kit_index(tmp_path):
    """키트의 자료/ 문서 다섯 개로 만든 색인(기본 설정: heading, 500자, 겹침 0, 제목 붙이기)."""
    return store.build_index(DOCS, tmp_path / "index")
