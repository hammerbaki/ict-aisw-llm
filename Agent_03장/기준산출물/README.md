# 2장 기준 산출물

2장(테스트 주도 개발)을 마치지 못한 학습자가 3장을 시작할 수 있도록 만든 2장 결과의 견본이다. 2장을 마친 학습자는 쓰지 않는다. 2장 키트(`Agent_02장`)의 도구와 설정을 그대로 가져왔고, 테스트는 2장보다 적다.

| 파일 | 내용 |
|---|---|
| `api/jobs.py` | `list_jobs()`에 `closing_within` 조건 추가(REQ-JOB-06) |
| `api/main.py` | `GET /api/jobs`의 `closing_within`(0 이상의 정수, 아니면 422), 요약 본문(4,000자)과 질문(500자)의 길이 검사 `check_length()`(REQ-SUM-05, REQ-ASK-06) |
| `tests/test_closing_within.py` | REQ-JOB-06의 테스트 6개(매개변수화 포함). `pytestmark = pytest.mark.req(id="REQ-JOB-06")` |
| `tests/test_summary_limits.py` | REQ-SUM-05의 테스트 4개 |
| `tests/test_ask_limits.py` | REQ-ASK-06의 테스트 4개 |
| `pytest.ini` | 2장 키트와 같다. 요구 마커 `req(id=...)`를 등록하고 `--strict-markers`를 켠다 |
| `tools/test_guard.py` | 2장 키트의 테스트 동결 검사기와 같다 |
| `requirements-dev.txt` | 2장 키트와 같다(coverage). 3장에서는 설치하지 않아도 된다 |
| `docs/요구사항명세서.md` | v1.2. 세 요구의 상태를 「구현」으로 바꾸고 테스트 파일을 적음 |

적용하면 `pytest -q`가 `57 passed`이다(기준 저장소 43개 + 14개. 2장을 직접 마치면 66개 안팎이다). 적용한 뒤 `tools/test_guard.py freeze`로 동결 기록 `tests/.baseline.json`을 만들고, 주석 태그 `tdd-1`을 붙인다. 명령은 강의안 0-3절에 있다. 2장에서 남기는 작업 브랜치 `feat/tdd-1`과 여러 커밋은 이 견본에 없다.
