"""색인에서 질문과 가까운 청크를 찾는다."""

import math

from rag.embedder import embed


def cosine_similarity(a, b):
    """두 벡터의 코사인 유사도. (a·b) / (|a| × |b|)이고, 한쪽이 영벡터이면 0이다."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(query, index, top_k=3):
    """질문과 유사도가 높은 순으로 청크 top_k개를 돌려준다.

    index는 rag.index.build_index()가 만든 dict이다. 질문은 색인을 만들 때와
    같은 임베딩 방식으로 바꾼다. 돌려주는 값은 [{"score": 유사도, "chunk": 청크}, ...]이다.
    """
    query_vector = embed(query, index["backend"])
    scored = []
    for chunk in index["chunks"]:
        score = cosine_similarity(query_vector, chunk["vector"])
        scored.append({"score": round(score, 4), "chunk": chunk})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]
