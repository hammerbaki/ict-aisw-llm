# 2장 키트: 테스트 주도 개발 (Agent_02장)

「AI에이전트 기획 및 개발」 2장(학사 3주차)의 실습 키트이다. 강의안은 `Agent_02장_학생용.md`이다. 기준 저장소 `jobprep`(1장)의 미구현 요구 셋(REQ-JOB-06, REQ-SUM-05, REQ-ASK-06)을 테스트로 쓰고, 동결하고, Claude Code로 통과시킨다. 사이클 2에서는 테스트 한 줄을 지워 「통과」를 만든 시도를 판정하고 되돌린다.

## 받기

내 PC의 Git Bash(macOS는 터미널)에서 키트 저장소를 최신으로 받고 이 장의 폴더를 `~/kits/`로 복사한다(부록 A-7-3).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_02장 ~/kits/
```

## 들어 있는 것

| 경로 | 내용 | 저장소에서의 자리 | 강의안 |
|---|---|---|---|
| `도구/test_guard.py` | 테스트 동결 검사기(freeze, freeze --update, check) | `tools/test_guard.py` | 7절, 0-4절 |
| `도구/돌려받은_시도.py` | 사이클 2의 「돌려받은 시도」를 저장소에 재현한다(파일 둘을 고치고 보고를 찍는다) | 옮기지 않는다. 저장소 맨 위에서 `python ~/kits/Agent_02장/도구/돌려받은_시도.py` | 11-5절 |
| `pytest.ini` | 요구 마커 `req(id=...)`를 등록하고 `--strict-markers`를 켠 설정 | 루트의 `pytest.ini`를 대신한다 | 0-4절, 4-5절 |
| `requirements-dev.txt` | 테스트용 패키지(`coverage==7.17.3`). `-r requirements.txt`를 포함한다 | 저장소 루트 | 0-4절, 10절 |
| `시작/tests/test_closing_within.py` | REQ-JOB-06의 테스트 시작 파일 | `tests/` | 11-2절 |
| `시작/tests/test_summary_limits.py` | REQ-SUM-05의 테스트 시작 파일 | `tests/` | 11-4절 |
| `시작/tests/test_ask_limits.py` | REQ-ASK-06의 테스트 시작 파일 | `tests/` | 11-6절 |
| `연습/test_연습_실패읽기.py` | 일부러 틀리게 쓴 테스트 넷(실패 화면 읽기). 강의안은 읽기로 다룬다 | 쳐 볼 때만 `tests/`에 잠시 넣고 지운다 | 3-6절 |
| `연습/test_연습_커버리지.py` | 단언 없는 테스트(커버리지의 한계) | [선택] `tests/`에 잠시 넣고 지운다 | 10-3절 |
| `지시문_양식.md` | Claude Code에 보내는 구현, 리팩터링, 재지시의 지시문 | 키트에 둔 채 쓴다 | 8절, 11절 |
| `실습기록_양식.md` | 사이클마다의 판정과 돌려받은 시도의 판정을 적는 표 | 키트에서 채우고 11-8절에 `docs/운영/2장_실습기록.md`로 | 11절 |
| `기준산출물/` | 1장을 마치지 못한 학습자용: 저장소 만들기 안내와 운영 문서 견본 | `docs/운영/` | 0-2절 |

## 순서

명령은 모두 저장소 맨 위(`~/agent-lab/jobprep`)에서, 가상 환경을 켠 터미널(Windows `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`)에서 친다.

1. 0-4절: 작업 브랜치 `feat/tdd-1`을 만들고 `도구/test_guard.py`, `pytest.ini`, `requirements-dev.txt`를 저장소에 넣는다. `python -m pip install -r requirements-dev.txt`. 커밋.
2. 7-6절(따라 하기 1): `python tools/test_guard.py freeze`로 기준선(테스트 43개)을 동결하고 커밋.
3. 9-4절(따라 하기 2): 판정을 바꾸는 시도를 손으로 일으키고 `git restore`, `git clean`으로 버린다.
4. 11절(핵심 실습): 요구마다 시작 파일 복사 → Red 확인 → 「할 일」 채우기 → Red 확인 → `freeze --update` → `test(...)` 커밋 → Claude Code에 지시 → 직접 `python -m pytest -q`와 `check` → `feat(...)` 커밋. 사이클 2에서는 지시 전에 `돌려받은_시도.py`를 실행해 판정하고 버린다.
5. 리팩터링, 명세서 갱신과 실습 기록의 커밋, `main`에 병합, 태그 `tdd-1`, 원격으로 푸시, 태그로 받아 재현 확인.

## 기대하는 화면

시작 파일은 그대로 실행된다. 정상 Red는 다음과 같다(테스트 43개인 기준 저장소에서 출발한 경우). 「할 일」을 채운 뒤의 수는 채운 만큼 달라진다. 2026-11-17에 Windows 11의 Git Bash, 파이썬 3.13.7, pytest 9.2.0에서 확인하였다.

| 단계 | 화면 |
|---|---|
| 기준선 동결(7-6절) | `동결 완료: 파일 8개 (tests/ 6개, 설정과 검사기 2개)` |
| 따라 하기 2의 시도 | `25 passed, 18 skipped`, `수정: tests/test_jobs.py`, `추가: conftest.py` |
| 시작 파일 `test_closing_within.py`만 넣은 직후 | `3 failed, 44 passed` |
| 할 일 1~7을 모두 채운 뒤 | `13 failed, 44 passed` (할 일 6~7을 빼면 `11 failed, 44 passed`), `freeze --update` 뒤 `파일 9개` |
| 사이클 1 Green | `57 passed` |
| `test_summary_limits.py` 시작 파일 / 채운 뒤 | `1 failed, 58 passed` / `3 failed, 59 passed`(정답 파일 기준) |
| 돌려받은 시도(11-5절) | `62 passed`인데 `TEST_CHANGED`, `수정: tests/test_summary_limits.py` |
| 사이클 2 Green | `62 passed` |
| `test_ask_limits.py` 시작 파일 / 채운 뒤 | `1 failed, 62 passed` / `3 failed, 63 passed` |
| 사이클 3 Green, 리팩터링 뒤 | `66 passed` |

동결 검사의 화면: `TEST_UNCHANGED (tests/.baseline.json 기준, 파일 N개)`, `TEST_CHANGED: 동결한 뒤 바뀐 파일이 있다`와 `수정:`, `삭제:`, `추가:` 목록.

## 주의

- 실제 LLM을 부르지 않는다. 기준 저장소의 `tests/conftest.py`가 모의 모드(`LLM_FAKE=1`)와 대체 임베딩을 켠다. API 키가 없어도 끝까지 돈다.
- 동결 기록 `tests/.baseline.json`은 저장소에 커밋한다. `freeze --update`는 사람만 실행한다.
- `돌려받은_시도.py`는 한 번만 실행한다. 두 번째에는 「자리를 찾지 못하였다」로 멈추고 아무것도 고치지 않는다.
- Windows의 Git Bash에는 `python3`이 없다. `python`으로 친다.
- 키트 저장소에 올릴 때 `교수/` 폴더는 빼고 올린다. 정답 테스트, 정답 구현, 숨은 테스트, 회피 시연 재료가 들어 있다.
