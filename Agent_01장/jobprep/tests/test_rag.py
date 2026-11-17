"""청킹, 임베딩, 검색, 색인의 테스트 (REQ-ASK-05 재현율)."""

import math
from pathlib import Path

import pytest

from rag.chunker import chunk_markdown
from rag.embedder import embed_fallback
from rag.index import get_index, recall_at_k
from rag.search import cosine_similarity, search

EVAL_CSV = Path(__file__).resolve().parent.parent / "rag" / "평가문항.csv"

SAMPLE = """# 안내
머리말은 청크가 되지 않는다.

## 첫째 절
첫째 본문이다.

## 둘째 절
둘째 본문이다.
"""


def test_chunk_by_section():
    chunks = chunk_markdown(SAMPLE, "sample.md")
    assert [c["title"] for c in chunks] == ["안내 > 첫째 절", "안내 > 둘째 절"]
    assert chunks[0]["id"] == "sample.md#1"
    assert chunks[1]["text"].startswith("# 안내\n## 둘째 절\n")
    assert "머리말" not in chunks[0]["text"]


def test_fallback_embedding_is_unit_length_and_deterministic():
    a = embed_fallback("모의면접 신청")
    assert a == embed_fallback("모의면접 신청")
    assert math.isclose(sum(v * v for v in a), 1.0, rel_tol=1e-9)


@pytest.mark.parametrize("a, b, expected", [
    ([1, 0], [1, 0], 1.0),
    ([1, 0], [0, 1], 0.0),
    ([1, 0], [-1, 0], -1.0),
    ([0, 0], [1, 0], 0.0),
])
def test_cosine_similarity(a, b, expected):
    assert math.isclose(cosine_similarity(a, b), expected, abs_tol=1e-9)


def test_search_returns_top_k_in_order():
    results = search("자격증 응시료 지원 한도", get_index(), top_k=3)
    assert len(results) == 3
    scores = [item["score"] for item in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["chunk"]["source"] == "05_자격증_응시료_지원.md"


def test_index_records_backend_and_chunks():
    index = get_index()
    assert index["backend"] == "fallback"
    assert len(index["chunks"]) >= 25
    assert {"id", "source", "title", "text", "vector"} <= set(index["chunks"][0])


def test_recall_at_3_is_at_least_80_percent():
    rate, hits, rows = recall_at_k(EVAL_CSV, get_index(), k=3)
    assert len(rows) == 10
    assert rate >= 0.8
