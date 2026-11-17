---
paths:
  - "api/**/*.py"
---
# api/ 규칙

- 엔드포인트는 `api/main.py`에 모으고, 처리 로직은 `api/jobs.py`, `api/summary.py`, `api/ask.py` 같은 모듈 함수로 둔다. 이유: 엔드포인트 함수는 입력 검사와 오류 변환만 한다.
- 잘못된 입력은 LLM을 부르기 전에 422로 거절한다. 길이와 범위 같은 조건은 명세서의 인수 조건을 그대로 따른다.
- 오류 응답은 `HTTPException(status_code, detail)`로 내고, `detail`은 한국어 한 문장으로 쓴다. 5xx 오류는 `error_log`에 `path=… status=… error=…` 형식으로 남긴다.
- 응답에 키, 환경 변수 값, 예외의 전체 추적 내용을 넣지 않는다(REQ-OPS-05).
- 새 엔드포인트를 만들면 `tests/`에 정상 1건과 오류 1건 이상의 테스트를 함께 만든다.
