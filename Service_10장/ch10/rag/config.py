# -*- coding: utf-8 -*-
"""RAG 설정. 모든 값은 환경 변수로 바꿀 수 있다.

설정을 함수로 읽는 까닭: 테스트와 실험에서 환경 변수를 바꾼 뒤 바로 반영되게 하기 위해서다.
값을 코드에 고쳐 쓰지 말고 환경 변수로 바꾼다(예: CHUNK_MAX_CHARS=200 python -m rag index).
"""
import os
from pathlib import Path

# ch10/ 폴더. rag/의 한 단계 위다.
ROOT = Path(__file__).resolve().parent.parent

# 근거가 없을 때 돌려주는 문장. 화면과 테스트가 이 문장을 그대로 쓴다.
NO_ANSWER = "제공된 취업 자료에는 이 질문에 대한 내용이 없습니다. 취업지원실(공학관 205호)에 문의하십시오."

# 임베딩 경로별 기본 기준값(1위 유사도가 이보다 낮으면 LLM을 부르지 않는다).
# fallback 값은 키트의 평가 문항과 범위 밖 문항으로 잰 값이다(python -m rag calibrate).
# ollama 값은 자리만 잡아 둔 값이다. 모델마다 눈금이 다르므로 그 모델로 calibrate를 돌려 다시 정한다.
DEFAULT_MIN_SCORE = {"fallback": 0.18, "ollama": 0.50}


def env(name, default):
    return os.environ.get(name, default)


def docs_dir():
    return Path(env("DOCS_DIR", str(ROOT / "자료")))


def index_dir():
    return Path(env("INDEX_DIR", str(ROOT / "rag" / "index")))


def embed_backend():
    """fallback(기본), ollama, auto 가운데 하나.

    fallback: 글자 n-gram 대체 구현. 설치가 필요 없고 누가 실행해도 같은 벡터가 나오므로
      재현율과 기준값이 학생마다 같은 값이 된다. 그래서 기본값으로 둔다.
    ollama: 내 PC에 설치한 Ollama의 임베딩 모델(선택, 부록 A-17). 연결할 수 없으면 오류를 낸다.
    auto: Ollama를 먼저 시도하고 안 되면 대체 구현. 설치 여부에 따라 결과가 달라지므로 측정에는 쓰지 않는다.
    """
    return env("EMBED_BACKEND", "fallback")


def embed_model():
    return env("EMBED_MODEL", "nomic-embed-text")


def ollama_url():
    return env("OLLAMA_URL", "http://127.0.0.1:11434")


def chunk_mode():
    """heading(제목 단위, 기본) 또는 size(고정 길이)."""
    return env("CHUNK_MODE", "heading")


def chunk_max_chars():
    return int(env("CHUNK_MAX_CHARS", "500"))


def chunk_overlap():
    return int(env("CHUNK_OVERLAP", "0"))


def chunk_add_title():
    """1이면 청크 앞에 「문서 제목 > 절 제목」을 붙여 임베딩한다."""
    return env("CHUNK_ADD_TITLE", "1") == "1"


def top_k():
    return int(env("TOP_K", "3"))


def search_method():
    """vector(기본), keyword, hybrid."""
    return env("SEARCH_METHOD", "vector")


def min_score(backend):
    value = os.environ.get("RAG_MIN_SCORE")
    if value is not None:
        return float(value)
    return DEFAULT_MIN_SCORE.get(backend, 0.0)


def max_turns():
    return int(env("MAX_TURNS", "4"))


def max_context_chars():
    """근거 블록 전체의 글자 수 상한. 넘으면 순위가 낮은 근거부터 뺀다."""
    return int(env("MAX_CONTEXT_CHARS", "3000"))
