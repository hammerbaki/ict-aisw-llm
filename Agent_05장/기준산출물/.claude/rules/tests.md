---
paths:
  - "tests/**/*.py"
---
# tests/ 규칙

- 새 테스트에는 요구 마커를 붙인다. 새 파일은 맨 위에 `pytestmark = pytest.mark.req(id="REQ-…")`를 두고, 기존 파일에 더하는 함수에는 바로 위에 `@pytest.mark.req(id="REQ-…")`를 붙인다. 이유: 요구 ID로 테스트를 고르고(`-m req`) 명세서와 잇는다(2장). `pytest.ini`가 `--strict-markers`이므로 마커 이름의 오타는 수집 오류가 된다.
- 테스트는 `conftest.py`가 정한 모의 모드에서 돈다. 실제 API, Ollama, 네트워크를 부르지 않는다.
- API는 `client` 픽스처로 부른다. 날짜가 걸린 테스트는 `monkeypatch.setattr(jobs, "today", lambda: date(2027, 9, 1))`로 기준일을 고정한다.
- LLM이 실패하는 경우는 `monkeypatch.setattr(llm, "complete", …)`로 만든다. `api/llm.py`를 고쳐 실패를 흉내 내지 않는다.
- 경계값은 양쪽을 모두 쓴다(예: 4,000자는 통과, 4,001자는 422).
