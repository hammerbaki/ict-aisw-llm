# -*- coding: utf-8 -*-
"""임베딩: 텍스트를 단위 길이 벡터로 바꾼다. (완성되어 있음)

두 경로가 있다.
- ollama: 내 PC에 설치한 Ollama가 제공하는 로컬 임베딩 모델(POST /api/embed). 선택이다(부록 A-17).
  응답의 embeddings는 입력 하나에 벡터 하나다. 여기서는 다시 L2 정규화한다.
- fallback(기본): 설치가 필요 없는 대체 구현. 글자 2-gram과 3-gram을 해시해 고정 길이 벡터로 만든다.
  의미를 이해하지 못하고 표면의 글자가 겹치는 정도만 잰다. 절차를 익히는 데는 충분하지만
  유사도 값과 재현율은 Ollama 모델과 다르다.

색인과 질문은 반드시 같은 경로, 같은 모델로 임베딩한다. store.py가 색인에 경로를 적어 두고 검사한다.
"""
import json
import sys
import urllib.error
import urllib.request
import zlib

import numpy as np

from . import config

FALLBACK_DIM = 2048
_state = {"backend": None}


def _normalize(matrix):
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _fallback_one(text):
    text = " ".join(text.lower().split())
    vec = np.zeros(FALLBACK_DIM, dtype=np.float32)
    for n in (2, 3):
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            if gram.strip() == "":
                continue
            vec[zlib.crc32(gram.encode("utf-8")) % FALLBACK_DIM] += 1.0
    return vec


def _embed_fallback(texts):
    return _normalize(np.vstack([_fallback_one(t) for t in texts]))


def _embed_ollama(texts):
    body = json.dumps({"model": config.embed_model(), "input": list(texts)}).encode("utf-8")
    request = urllib.request.Request(
        config.ollama_url() + "/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read())
    return _normalize(np.array(data["embeddings"], dtype=np.float32))


def current_backend():
    """이번 실행에서 쓰는 경로(ollama 또는 fallback)를 정해 돌려준다."""
    if _state["backend"] is None:
        wanted = config.embed_backend()
        if wanted == "fallback":
            _state["backend"] = "fallback"
        else:
            try:
                _embed_ollama(["연결 확인"])
                _state["backend"] = "ollama"
            except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
                if wanted == "ollama":
                    raise RuntimeError(f"Ollama에 연결할 수 없다: {config.ollama_url()} ({e})") from e
                print(f"[대체 임베딩] Ollama({config.ollama_url()}, {config.embed_model()})에 연결할 수 없어 "
                      f"글자 n-gram 대체 구현을 쓴다. ({type(e).__name__})", file=sys.stderr)
                _state["backend"] = "fallback"
    return _state["backend"]


def reset():
    """경로 선택을 지운다(테스트와 실험용)."""
    _state["backend"] = None


def embed_texts(texts):
    """텍스트 목록을 (개수, 차원) 크기의 정규화된 행렬로 바꾼다."""
    if current_backend() == "ollama":
        return _embed_ollama(texts)
    return _embed_fallback(texts)


def embed_text(text):
    return embed_texts([text])[0]


def describe():
    backend = current_backend()
    return {"backend": backend, "model": config.embed_model() if backend == "ollama" else f"char-ngram-{FALLBACK_DIM}"}
