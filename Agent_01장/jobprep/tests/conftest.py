"""모든 테스트가 같은 조건에서 돌도록 환경을 정한다.

- LLM_FAKE=1: 실제 API를 부르지 않는다.
- EMBED_BACKEND=fallback: Ollama가 있는 컴퓨터와 없는 컴퓨터에서 결과가 같도록 대체 임베딩을 쓴다.
- RAG_INDEX_PATH: 테스트용 색인을 임시 폴더에 만들어 저장소의 색인 파일을 건드리지 않는다.
환경 변수는 앱을 불러오기 전에 정해야 하므로 이 파일의 맨 위에서 정한다.
"""

import os
import tempfile

os.environ["LLM_FAKE"] = "1"
os.environ["EMBED_BACKEND"] = "fallback"
os.environ["RAG_INDEX_PATH"] = os.path.join(tempfile.mkdtemp(prefix="jobprep-test-"), "index.json")
os.environ.pop("LOG_DIR", None)
os.environ.pop("ASK_MIN_SCORE", None)
os.environ.pop("PROMPT_SUMMARY", None)
os.environ.pop("PROMPT_ASK", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


@pytest.fixture
def client():
    """API를 서버 없이 부르는 테스트 클라이언트."""
    return TestClient(app)


@pytest.fixture
def job_text(client):
    """요약 테스트에 쓰는 공고 본문(1번 공고)."""
    job = client.get("/api/jobs/1").json()
    return f"{job['title']} / {job['company']}\n마감일: {job['deadline']}\n{job['description']}"
