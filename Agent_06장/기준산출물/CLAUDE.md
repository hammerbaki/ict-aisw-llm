# jobprep 팀 규칙

이 파일은 6장 키트의 기준 산출물이다. 3장에서 쓴 `CLAUDE.md`가 있으면 그것을 쓴다.

## 실행

- 가상 환경: 터미널마다 먼저 켠다. Windows Git Bash `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`. 그 뒤로는 `python`으로 부른다(`python3`을 쓰지 않는다)
- 테스트: `python -m pytest` (모의 모드로 돈다. API 키가 없어도 통과해야 한다)
- 동결 검사: `python tools/test_guard.py check` (`TEST_UNCHANGED`가 정상)
- API 서버: `LLM_FAKE=1 uvicorn api.main:app --reload --port 8000`

## 규칙

1. 비밀 정보: API 키는 `.env`에만 둔다. 코드, 설정, 문서, 기록에 키를 적지 않는다. `.env`는 읽지도 고치지도 않는다.
2. LLM 호출: 모든 LLM 호출은 `api/llm.py`의 `complete()`를 거친다. 코드에 모델 이름을 적지 않는다(`LLM_MODEL`).
3. 웹 출력: 화면에 글을 넣을 때는 `textContent` 또는 `el()`만 쓴다. `innerHTML`을 쓰지 않는다.
4. 테스트: 동결된 테스트(`tests/.baseline.json`에 기록된 파일)는 고치지 않는다. 새 요구는 새 테스트로 더한다.
5. 오류 처리: 예외를 잡으면 기록하고 다시 던지거나 알맞은 HTTP 오류로 바꾼다. 빈 값으로 숨기지 않는다.
6. 모의 모드: 테스트는 `LLM_FAKE=1`로 돈다. 테스트에서 실제 API를 부르지 않는다.

## 작업 방식

- 구현을 고친 뒤에는 관련 테스트를 돌리고 결과를 보고한다.
- 보호된 파일을 바꾸어야 한다고 판단되면 고치지 말고 까닭을 보고한다.
