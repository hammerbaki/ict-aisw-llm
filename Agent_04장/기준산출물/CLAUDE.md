<!-- 이 파일은 팀 공용이다. 고치려면 PR을 열고 CODEOWNERS의 검토를 받는다. 개인 취향은 CLAUDE.local.md에 둔다. -->
# jobprep

취업 준비 지원 서비스이다. 백엔드는 FastAPI(`api/`), 검색은 `rag/`, 화면은 빌드 도구 없는 정적 웹(`web/`)이다.
공고와 취업 자료, 운영 기록은 모두 실습용 가상 자료이다.
요구와 그 상태는 `docs/요구사항명세서.md`, 운영 문서는 `docs/운영/`에 있다.

## 실행 명령

터미널마다 가상 환경을 먼저 켜고(Windows Git Bash `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`) 그 뒤로는 `python`으로 부른다. `python3`과 `.venv/bin/python …` 같은 경로 호출은 쓰지 않는다(Windows Git Bash에는 `python3`이 없고, 경로 호출은 팀 설정의 허용 규칙에 맞지 않는다).

- 전체 테스트: `python -m pytest -q` (모의 모드로 돌아 API 키가 필요 없다. 약 3초)
- 테스트 하나: `python -m pytest -q tests/test_jobs.py::test_list_is_sorted_by_deadline`
- 요구 하나의 테스트: `python -m pytest -q -m "req(id='REQ-JOB-06')"`
- 테스트 동결 검사: `python tools/test_guard.py check` (`TEST_UNCHANGED`가 정상)
- API 서버: `LLM_FAKE=1 uvicorn api.main:app --reload --port 8000` (문서는 `http://127.0.0.1:8000/docs`. 8000을 다른 프로그램이 쓰는 PC에서는 다른 번호를 쓰고, 그 값은 `CLAUDE.local.md`에 둔다)
- 규칙 검사: `python ops/rules/lint_rules.py`
- 커밋 메시지 검사: `python ops/rules/check_commits.py --range main..HEAD`

## 작업 규칙

- 기능을 바꾸기 전에 실패하는 테스트를 `tests/`에 먼저 쓴다. 완료 조건은 전체 테스트 통과이다. 테스트를 더하면 동결 검사가 `TEST_CHANGED`를 내는 것이 정상이며, 그 사실을 보고에 적는다.
- 새 요구는 `docs/요구사항명세서.md`에 REQ-ID를 붙여 적고, 테스트 열에 테스트 이름을 쓴다.
- LLM 호출은 `api/llm.py`의 `complete()`만 거친다. 이유: 모의 모드, 프롬프트 판본, 호출 기록이 이 한 곳에서 처리된다.
- 모델 이름은 환경 변수 `LLM_MODEL`로만 받고 코드에 적지 않는다. 이유: 모델을 바꿀 때 코드를 고치지 않는다(REQ-OPS-03).
- 웹 화면에 글을 넣을 때는 `textContent`(`web/js/common.js`의 `el()`)만 쓴다. 이유: 공고 본문과 LLM 출력이 HTML로 해석되면 스크립트가 실행될 수 있다.
- `api/`와 `rag/`의 기록은 `logging`의 `jobprep.*` 기록기로 남기고 `print`를 쓰지 않는다. 이유: 운영 기록의 형식(`logs/README.md`)을 지킨다.
- 브랜치 이름과 커밋 메시지는 `docs/운영/저장소규약.md`를 따른다. 커밋 첫 줄은 `feat(api): 설명` 꼴이다.

## 금지

- `.env`를 읽거나 출력하거나 커밋하지 않는다. 이유: 각자 발급한 API 키가 들어 있을 수 있다(settings.json에서도 거부한다).
- 기존 테스트를 지우거나 기대값을 바꾸어 통과시키지 않는다. 이유: 테스트가 완료 조건이다. 테스트가 틀렸다고 판단되면 고치지 말고 알린다.
- `tests/.baseline.json`, `pytest.ini`, `conftest.py`, `tools/test_guard.py`를 고치지 않고 `test_guard.py freeze`를 실행하지 않는다. 이유: 판정 기준은 사람이 정하고 잠근다(2장). 동결 기록의 갱신은 사람이 diff를 읽은 뒤에 한다.
- `data/`의 공고와 자료를 고치지 않는다. 이유: 테스트와 검색 평가 문항이 이 자료에 맞추어져 있다.
- `main` 브랜치에 직접 커밋하거나 푸시하지 않는다. 이유: 모든 변경은 PR 검토를 거친다.
- `requirements.txt`에 패키지를 더하거나 판을 바꾸지 않는다. 이유: 판을 고정해 같은 결과를 다시 얻는다. 필요하면 PR 설명에 까닭을 적어 사람에게 넘긴다.
