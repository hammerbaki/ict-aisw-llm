"""평가 도구의 테스트 환경. tests/conftest.py와 같은 조건(모의 모드, 대체 임베딩, 임시 색인)을 쓴다."""

import os
import tempfile

os.environ["LLM_FAKE"] = "1"
os.environ["EMBED_BACKEND"] = "fallback"
os.environ["RAG_INDEX_PATH"] = os.path.join(tempfile.mkdtemp(prefix="jobprep-evals-test-"), "index.json")
os.environ.pop("PROMPT_SUMMARY", None)
os.environ.pop("PROMPT_ASK", None)
