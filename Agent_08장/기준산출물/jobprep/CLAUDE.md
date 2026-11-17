# jobprep: 팀 규칙

이 파일은 7장 키트의 「조립한 판」 견본이다. 기준 산출물의 `CLAUDE.md`에서 훅이 강제하는 일과 겹치는 지시를 고쳤다(7장 5절).

취업 준비 지원 서비스 `jobprep`의 저장소이다. FastAPI 백엔드(`api/`), 검색(`rag/`), 정적 웹(`web/`), 운영 기록 견본(`logs/`), 운영 문서(`docs/운영/`)로 되어 있다. 서비스 요구는 `docs/요구사항명세서.md`에 있다.

## 명령

터미널마다 가상 환경을 먼저 켜고(Windows Git Bash `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`) 그 뒤로는 `python`으로 부른다. `python3`과 `.venv/bin/python …` 같은 경로 호출은 쓰지 않는다.

- 테스트: `python -m pytest` (모의 모드. `tests/conftest.py`가 `LLM_FAKE=1`을 켠다)
- 서버: `LLM_FAKE=1 uvicorn api.main:app --reload --port 8000`

## 지킬 것

1. 비밀 정보: API 키는 `.env`에만 둔다. 코드, 설정, 문서, 기록, 커밋 메시지에 키를 적지 않는다. `.env`는 읽지도 고치지도 않는다. 왜냐하면 저장소는 팀 밖으로 복제될 수 있기 때문이다.
2. LLM 호출: 모든 LLM 호출은 `api/llm.py`의 `complete()`를 거친다. 코드에 모델 이름을 적지 않는다(`LLM_MODEL`).
3. 웹 출력: 화면에 글을 넣을 때는 `textContent` 또는 `el()`만 쓴다. `innerHTML`을 쓰지 않는다.
4. 테스트: 동결된 테스트(`tests/.baseline.json`에 기록된 파일)는 고치지 않는다. 새 요구는 새 테스트 파일로 더한다.
5. 오류 처리: 예외를 잡으면 기록하고 다시 던지거나 알맞은 HTTP 오류로 바꾼다. 빈 값으로 숨기지 않는다.
6. 모의 모드: 테스트는 `LLM_FAKE=1`로 돈다. 테스트에서 실제 API를 부르지 않는다.
7. 기록: 기록(logging)에 질문 원문, 공고 본문, 키를 남기지 않는다. 글자 수나 개수만 남긴다(`logs/README.md`).
8. 명세: 기능을 더하거나 바꾸면 `docs/요구사항명세서.md`의 해당 요구 행(REQ-ID, 상태, 테스트)을 함께 고친다.

## 작업 방식

- 보고에는 마지막으로 실행한 테스트 명령과 결과의 마지막 줄을 붙인다. 테스트 실행은 훅(편집 뒤, 끝내기 전)이 강제한다.
- 보호된 파일을 바꾸어야 한다고 판단되면 고치지 말고 까닭을 보고한다.
- 커밋 하나에 변경 하나. 커밋 메시지는 `docs/운영/저장소규약.md`의 형식(`종류(범위): 내용`)을 따른다.
- 운영 기록을 조사할 때는 MCP 서버 `jobprep-ops`의 도구나 `jobprep-ops` 플러그인의 `incident-report` 스킬을 쓴다.
