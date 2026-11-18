# -*- coding: utf-8 -*-
"""검색 고정 테스트. 고치지 않는다. vector_search를 완성하면 통과한다."""
import numpy as np
import pytest

from rag import search, store


def toy_index(monkeypatch, query_vector):
    """임베딩을 정해 둔 벡터로 바꿔 끼운 작은 색인."""
    monkeypatch.setattr(search.embedder, "embed_text", lambda text: np.array(query_vector, dtype=np.float32))
    vectors = np.array([[0.0, 1.0], [1.0, 0.1], [0.7071, 0.7071], [-1.0, 0.0]], dtype=np.float32)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    chunks = [{"id": f"t#{i}", "source": "t", "title": "t", "heading": name, "sections": [name],
               "text": name, "embed_text": name}
              for i, name in enumerate(["직각", "거의 같은 방향", "45도", "반대 방향"], 1)]
    return store.Index(chunks, vectors, {"backend": "fallback"})


def test_벡터_검색은_유사도가_높은_순으로_k개를_돌려준다(monkeypatch):
    index = toy_index(monkeypatch, [1.0, 0.0])
    hits = search.vector_search("아무 질문", index, 3)
    assert [h["chunk"]["heading"] for h in hits] == ["거의 같은 방향", "45도", "직각"]
    assert [h["rank"] for h in hits] == [1, 2, 3]
    assert hits[0]["score"] >= hits[1]["score"] >= hits[2]["score"]
    assert hits[0]["similarity"] == pytest.approx(hits[0]["score"])
    assert isinstance(hits[0]["score"], float)


def test_k가_청크_수보다_크면_청크_수만큼_돌려준다(monkeypatch):
    index = toy_index(monkeypatch, [1.0, 0.0])
    assert len(search.vector_search("질문", index, 10)) == 4


def test_키트_자료에서_벡터_검색의_1위가_맞는_절이다(kit_index):
    hits = search.search("취업지원실은 몇 시까지 문을 열어?", kit_index, k=3, method="vector")
    assert hits[0]["chunk"]["heading"] == "취업지원실 운영 시간과 위치"


def test_키워드_검색은_같은_낱말이_든_청크를_찾는다(kit_index):
    hits = search.keyword_search("누리소프트 마감", kit_index, 3)
    assert hits[0]["chunk"]["source"] == "채용공고_발췌"
    assert hits[0]["chunk"]["heading"].startswith("공고 A")


def test_혼합_검색은_두_순위를_합친다(kit_index):
    hits = search.hybrid_search("현장실습 성적 평가", kit_index, 3)
    assert len(hits) == 3
    assert hits[0]["score"] >= hits[1]["score"] >= hits[2]["score"]
