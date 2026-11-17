# jobprep 프로젝트 규칙 (기준 산출물 견본)

## 개요
- 취업 준비 지원 서비스. 대상 사용자는 전문대학 2학년 취업 준비생이다(페르소나 PS-1 서지후, PS-2 임하람).
- 명세는 `docs/요구사항명세서.md`(현재 판 v5, 태그 `spec-v5`)가 기준이다.
- 백엔드는 `api/`(FastAPI, 앱은 `api/app.py`의 `app`), 화면은 `web/`(빌드 도구 없는 HTML·CSS·자바스크립트)이다.
- LLM 호출은 `api/llm.py`의 `complete()` 한 곳을 지난다.

## 실행 (jobprep 폴더에서. 저장소 맨 위의 가상 환경 `.venv`를 켠 터미널)
- 테스트: `python -m pytest`
- 서버: `python -m uvicorn api.app:app --port 8000` (API 8000, 웹은 같은 서버의 `http://localhost:8000/`. 부록 A-16)

## 규칙
- 구현을 바꾸기 전에 명세서의 해당 요구를 먼저 고친다. 명세 변경과 구현은 같은 커밋에 묶고, 커밋 메시지 끝에 요구 ID(예: `REQ-013`)를 적는다.
- `tests/` 아래 파일은 고치지 않는다.
- API 키와 모델 이름을 코드에 쓰지 않는다. 키는 `jobprep/.env`에만 두고(`.gitignore` 처리), 모델은 `LLM_MODEL`로 읽는다.
- LLM을 부르는 코드는 `LLM_FAKE=1`이면 API를 부르지 않아야 한다.
