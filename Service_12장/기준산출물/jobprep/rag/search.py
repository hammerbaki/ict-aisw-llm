# -*- coding: utf-8 -*-
"""검색: 벡터 검색, 키워드 검색(BM25), 혼합 검색(RRF).

검색 결과(hit) 하나는 다음 키를 가진 사전이다.
    rank        1부터 시작하는 순위
    score       순위를 정한 점수(방법마다 눈금이 다르다)
    similarity  질문 벡터와 청크 벡터의 코사인 유사도(모든 방법에서 계산한다. 기준값 판정에 쓴다)
    chunk       청크 사전(chunker.py 참고)
"""
import math
import re
from collections import Counter

import numpy as np

from . import config, embedder

RRF_K = 60       # RRF의 상수 k. 순위가 낮은 결과의 영향을 얼마나 남길지 정한다
CANDIDATES = 20  # 혼합 검색에서 각 방법이 내놓는 후보 수


def cosine_scores(query, index):
    """질문과 모든 청크의 코사인 유사도 배열. 벡터가 정규화되어 있으므로 내적과 같다."""
    q = embedder.embed_text(query)
    return index.vectors @ q


def vector_search(query, index, k):
    """질문과 코사인 유사도가 높은 순으로 청크 k개를 돌려준다. [실습에서 완성]

    순서
    1. cosine_scores(query, index)로 모든 청크의 유사도 배열을 얻는다.
    2. 유사도가 높은 순으로 청크 번호를 정렬한다(np.argsort를 쓰고 뒤집는다).
    3. 앞의 k개로 hit 사전 목록을 만든다. rank는 1부터, score와 similarity는 같은 유사도(float),
       chunk는 index.chunks[번호]다.
    k가 청크 수보다 크면 청크 수만큼만 돌려준다.
    """
    scores = cosine_scores(query, index)
    order = np.argsort(scores)[::-1][:k]
    return [
        {"rank": r, "score": float(scores[i]), "similarity": float(scores[i]), "chunk": index.chunks[i]}
        for r, i in enumerate(order, 1)
    ]


def tokenize(text):
    """키워드 검색용 낱말 나누기. 띄어쓰기 단위로 자르고 기호를 뺀다.

    한국어는 조사가 붙어(「자기소개서는」, 「자기소개서를」) 같은 낱말도 다른 토큰이 된다.
    실무의 키워드 검색은 형태소 분석기로 조사를 떼어 낸다. 이 키트는 일부러 단순하게 두었다.
    """
    return re.findall(r"[0-9a-z가-힣]+", text.lower())


def keyword_search(query, index, k, k1=1.2, b=0.75):
    """BM25로 점수를 매겨 상위 k개를 돌려준다. (완성되어 있음)"""
    docs = [tokenize(c["embed_text"]) for c in index.chunks]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n
    df = Counter(t for d in docs for t in set(d))
    q_terms = tokenize(query)
    scores = []
    for d in docs:
        tf = Counter(d)
        s = 0.0
        for t in q_terms:
            if tf[t] == 0:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    sims = cosine_scores(query, index)
    order = sorted(range(n), key=lambda i: -scores[i])[:k]
    return [
        {"rank": r, "score": scores[i], "similarity": float(sims[i]), "chunk": index.chunks[i]}
        for r, i in enumerate(order, 1)
    ]


def hybrid_search(query, index, k):
    """벡터 검색과 키워드 검색의 순위를 RRF로 합친다. (완성되어 있음)

    RRF 점수 = 각 방법에서의 1 / (RRF_K + 순위)의 합. 두 방법의 점수 눈금이 달라도
    순위만 쓰므로 그대로 더할 수 있다.
    """
    lists = [vector_search(query, index, CANDIDATES), keyword_search(query, index, CANDIDATES)]
    fused, sims, chunks = {}, {}, {}
    for hits in lists:
        for h in hits:
            cid = h["chunk"]["id"]
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + h["rank"])
            sims[cid] = h["similarity"]
            chunks[cid] = h["chunk"]
    order = sorted(fused, key=lambda cid: -fused[cid])[:k]
    return [
        {"rank": r, "score": fused[cid], "similarity": sims[cid], "chunk": chunks[cid]}
        for r, cid in enumerate(order, 1)
    ]


def search(query, index, k=None, method=None):
    k = k or config.top_k()
    method = method or config.search_method()
    if method == "vector":
        return vector_search(query, index, k)
    if method == "keyword":
        return keyword_search(query, index, k)
    if method == "hybrid":
        return hybrid_search(query, index, k)
    raise ValueError("SEARCH_METHOD는 vector, keyword, hybrid 가운데 하나다")
