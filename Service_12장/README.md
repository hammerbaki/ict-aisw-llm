# Service_12장: 다중 프로덕트의 비교 구현 (실습 키트)

「LLM 서비스 개발」 12장의 키트다. 같은 명세(자기소개서 피드백, REQ-080~REQ-089)로 양식형(`variant-form`)과 대화형(`variant-chat`) 두 구현을 Orca의 작업 공간 두 개에서 나란히 만들고, 측정값으로 비교 기준표를 채우고, 두 구현이 서로 다르게 정한 곳(명세의 빈틈)을 EARS로 보강하고, 결정 기록(ADR)을 쓰고, 하나를 병합한다.

## 받기 (내 PC의 터미널: Windows는 Git Bash, macOS는 기본 터미널)

```bash
git -C ~/kits-repo pull                                            # 키트 저장소(부록 A-12-2)
mkdir -p ~/kits && cp -rn ~/kits-repo/Service_12장 ~/kits/        # 키트는 저장소 밖에 둔다(부록 A-12-3)
source ~/llm-service-lab/.venv/Scripts/activate                    # macOS: source ~/llm-service-lab/.venv/bin/activate (부록 A-13)
cd ~/kits/Service_12장
python -m pip install -r requirements.txt
python -m pytest -q
```

`python -m pytest -q`는 키트 도구의 검사 9개가 모의 모드에서 통과하는지 본다(서버와 API 키가 필요 없다). 검사가 기준 산출물의 앱을 불러 오므로 `requirements.txt`는 기준 산출물(11장 완성판)과 같은 패키지를 고정한다. 테스트는 `교수/` 폴더를 읽지 않으므로, `교수/`가 없는 학생 키트에서도 9개가 모두 돈다.

## 들어 있는 것

| 경로 | 쓰는 절 | 내용 |
|---|---|---|
| `명세추가_자기소개서피드백.md` | 2-5(따라 하기 1) | 명세서에 붙일 「자기소개서 피드백」 절(REQ-080~089) |
| `비교구현_양식.md` | 2-5, 9-5~9-8 | 비교 기준표 → `jobprep/docs/비교구현.md` |
| `변형지시_공통_양식.md`, `변형지시_form_양식.md`, `변형지시_chat_양식.md` | 4-3(따라 하기 2), 9-4 | 같은 명세를 두 번 주는 지시문. 공통 부분과 변형별 차이로 나뉜다 |
| `연습/` | 5-9(따라 하기 3), 6-4 | 비교 도구를 익히는 작은 재료(마감 임박 표시) |
| `검사어댑터/form.json`, `chat.json` | 5-3, 9-5 | 공통 자동 검사가 변형마다 요청을 보내고 응답을 읽는 방법 |
| `시나리오/form.json`, `chat.json`, `답변_초안.txt`, `답변_수정.txt` | 5-4, 9-7 | 응답 시간과 토큰을 재는 과업(양식형 요청 2회, 대화형 요청 3회) |
| `시나리오/요청_짧은답변.json`, `요청_초과_form.json`, `요청_초과_chat.json` | 9-6 | `curl`로 REQ-082, REQ-083을 확인하는 요청(제한 300자) |
| `명세점검표_양식.md` | 5-2, 9-6 | 명세 충족 점검표 |
| `추출명세_양식.md` | 6절, 9-8 [선택] | 구현에서 다시 뽑은 명세의 표(대응 칸 포함) |
| `결정기록_양식.md` | 7절, 9-9 | ADR → `jobprep/docs/결정/ADR-001-….md` |
| `도구/` | 5~6절, 9절 | 아래 표 |
| `tests/` | 0-1 | 도구의 검사 |
| `기준산출물/jobprep/` | 0-3 | 9~11장 산출물이 없는 학습자를 위한 견본. 11장 키트의 완성 상태(10장 키트 완성 상태, 9·10장 웹, 11장 완성판)에 0-3절의 확장(`api/llm.py`의 `messages`·`purpose`·호출 기록, `rag/llm.py`가 `complete()`를 부름, `tests/conftest.py`의 기록 경로)을 마친 판. 명세서는 7장 정본 v2에 10·11장 변경을 더한 v6 견본. `docs/추적표.md`(6장에서 시작해 8장까지 채운 9장 기준 산출물의 표)와 `docs/인수조건.md`(9장 견본)를 2026-11-17에 더하였다 |
| `시연기록/` | 5-10 [선택] | 교수가 실제 모델로 두 변형을 잰 기록(호출 기록 둘, 시간 CSV 둘, 요약). 교수가 수업 전에 키트 저장소에 올린다. 지금은 안내 파일만 있다 |
| `교수/` | 교수용 | 두 변형의 견본 구현, 견본 비교 문서, 시연 저장소 스크립트(Orca 없이 `git worktree` 명령으로 같은 흐름을 만든다), 실제 호출 기록을 만드는 스크립트. 학생 키트 저장소에 넣지 않는다 |

## 도구

| 도구 | 하는 일 | 예 |
|---|---|---|
| `prepare_base.py` | 기준 산출물을 저장소에 채운다(있는 파일은 건너뜀) | `python 도구/prepare_base.py ~/llm-service-lab` |
| `check_common.py` | 두 변형에 같은 자동 검사 5개(REQ-081·082·083·086·087) | `python 도구/check_common.py --app-dir <jobprep> --adapter 검사어댑터/form.json` |
| `measure_latency.py` | 시나리오를 반복해 과업 시간의 중앙값을 잰다 | `python 도구/measure_latency.py --base http://127.0.0.1:8000 --scenario 시나리오/form.json` |
| `token_report.py` | 호출 기록을 변형별로 모아 호출 수, 토큰, 어림 비용을 낸다 | `python 도구/token_report.py <기록.jsonl> --tasks 6 --price-in 1 --price-out 5` |
| `spec_checklist.py` | 점검표의 판정을 세어 충족률을 낸다 | `python 도구/spec_checklist.py 점검표_form.md 점검표_chat.md` |
| `spec_diff.py` | 원 명세와 추출 명세의 요구 ID 집합을 대조한다 | `python 도구/spec_diff.py 요구사항명세서.md --range REQ-080~089 form=… chat=…` |

## 포트

두 변형의 서버를 같은 PC에서 동시에 띄우므로 양식형은 8000, 대화형은 8001을 쓴다(부록 A-16의 고정 포트 8000에, 둘째 서버만 다른 번호). 각 서버가 자기 변형의 웹을 같은 출처에서 보내므로 8100의 정적 서버는 쓰지 않는다(10장). 포트가 이미 쓰이면 `netstat -ano | findstr :8000`(부록 A-16-1).

## 모의 모드

`jobprep/api/llm.py`는 `LLM_FAKE=1`이면 API를 부르지 않고 정해진 응답을 낸다(`.env.example`의 기본값이 1이다).

- `LLM_FAKE_LATENCY=on`: 응답 시간을 흉내 낸다(300ms + 출력 토큰당 4ms). 모의 모드의 시간은 실제 모델의 시간이 아니다.
- `LLM_FAKE_FAIL=1`: 호출 실패를 일으킨다(REQ-086 확인).
- 호출 기록 `api/logs/llm_calls.jsonl`에는 시각, 변형(`JOBPREP_VARIANT`), 용도, 토큰 수, 걸린 시간만 남는다. 모의 모드의 토큰은 글자 수에 0.8을 곱해 어림한 값이다(10장과 같다).
- 이 장의 측정은 모두 모의 모드로 한다. 실제 모델로 같은 과업을 되풀이해 재는 것(5-10)은 실행 상한을 넘으므로 교수 시연이며, 학생은 `시연기록/`의 기록을 읽는다. 각자 Console 키를 발급한 학생도 반복 측정은 하지 않는다(사용자 결정 11).

## 확인한 환경

- 2026-11-14, Windows 11, Python 3.13.7, git 2.55.0, fastapi 0.162.7, uvicorn 0.54.0, pytest 9.2.0, anthropic 2.8.0(실제 호출은 하지 않음).
- 2026-11-17, Windows 11(빌드 26300)의 Git Bash, Python 3.13.7 가상 환경에 이 `requirements.txt`만 설치해 학생 키트(`교수/` 제외)와 교수 사본에서 `python -m pytest -q`, 학생용 0절·따라 하기·핵심 실습의 명령(Orca 화면 조작은 `git worktree add`로 대신). Orca 화면과 macOS는 확인하지 못하였다.
