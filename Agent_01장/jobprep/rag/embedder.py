"""글을 임베딩 벡터(숫자 목록)로 바꾼다.

두 가지 방식이 있다.
- ollama: 실습 서버의 Ollama가 제공하는 임베딩 모델을 부른다(의미를 반영한다).
- fallback: 설치가 필요 없는 대체 구현. 글자 두 개씩 묶은 조각(bigram)을 세어
  고정 길이 벡터로 만든다. 의미는 모르고 표현이 겹치는 정도만 잰다.

환경 변수
- EMBED_BACKEND: "auto"(기본, Ollama가 응답하면 ollama, 아니면 fallback), "ollama", "fallback"
- OLLAMA_URL: Ollama 주소(기본 http://localhost:11434)
- EMBED_MODEL: Ollama 임베딩 모델 이름(기본 nomic-embed-text)

색인과 질문은 같은 방식으로 임베딩해야 한다. 색인 파일에 방식을 적어 두는 까닭이다.
"""

import json
import math
import os
import urllib.error
import urllib.request

FALLBACK_DIM = 1024
_auto_choice = None  # "auto"일 때 한 번 정한 방식을 기억한다


def ollama_url():
    return os.environ.get("OLLAMA_URL", "http://localhost:11434")


def ollama_model():
    return os.environ.get("EMBED_MODEL", "nomic-embed-text")


def choose_backend():
    """이번 실행에서 쓸 임베딩 방식("ollama" 또는 "fallback")을 정한다."""
    global _auto_choice
    wanted = os.environ.get("EMBED_BACKEND", "auto")
    if wanted in ("ollama", "fallback"):
        return wanted
    if _auto_choice is None:
        try:
            embed_ollama("연결 확인", timeout=3)
            _auto_choice = "ollama"
        except (OSError, ValueError, KeyError, IndexError):
            _auto_choice = "fallback"
    return _auto_choice


def embed(text, backend):
    """text를 backend 방식으로 임베딩한다."""
    if backend == "ollama":
        return embed_ollama(text)
    return embed_fallback(text)


def embed_ollama(text, timeout=30):
    """Ollama의 /api/embed를 부른다. 연결하지 못하면 OSError 계열의 예외가 난다."""
    body = json.dumps({"model": ollama_model(), "input": text}).encode("utf-8")
    request = urllib.request.Request(
        ollama_url() + "/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read())
    return data["embeddings"][0]


def embed_fallback(text):
    """대체 임베딩: bigram을 해시해 FALLBACK_DIM 칸에 세고, 길이를 1로 맞춘다."""
    text = " ".join(text.lower().split())
    vector = [0.0] * FALLBACK_DIM
    grams = [text[i:i + 2] for i in range(len(text) - 1)] or [text]
    for gram in grams:
        if gram.strip() == "":
            continue
        code = 0
        for ch in gram:
            code = (code * 131 + ord(ch)) % 1000003
        vector[code % FALLBACK_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]
