# Service_09장: LLM 기능의 설계와 API 연동 키트

「LLM 서비스 개발」 9장(학사 11주차, 서비스 4 「문서 요약과 질의응답」의 1/2)의 실습 재료이다. 공고 요약 API(FastAPI)를 띄우고, 프롬프트 판본 세 개를 평가 문항 10개로 비교해 하나를 채택한다. 모든 코드는 모의 모드(`LLM_FAKE=1`)에서 키 없이 끝까지 돈다. 앞 장의 산출물이 없어도 시작할 수 있다.

## 들어 있는 것

| 경로 | 내용 | 쓰는 절 |
|---|---|---|
| `ch09/api/` | 요약 API. `app.py`(FastAPI), `llm.py`(호출을 한 곳에 모음, 모의 모드), `schema.py`(요약 형식), `prompts.py`(판본 파일 읽기), `fake.py`(모의 요약기) | 1, 2, 5, 8절 |
| `ch09/prompts/` | 프롬프트 판본 `v1.md`(기준선), `v2.md`(규칙과 형식), `v3.md`(v2 + 예시 두 건) | 6절 |
| `ch09/eval/` | 평가 문항(가상 공고 10건 `공고/`, 정답 `정답.json`), 채점기 `grader.py`, 판본 비교 실행기 `run_compare.py`, 모의 응답 `모의응답/` | 4, 7, 11절 |
| `ch09/tools/` | `first_call.py`(요청 한 번의 구조 보기), `count_tokens.py`(토큰 세기), `cost_estimate.py`(월 비용 어림), `check_secrets.py`(키 노출 검사) | 2, 10, 11절 |
| `ch09/tests/` | pytest 테스트 42개. 모의 모드에서 모두 통과한다 | 0, 7, 11절 |
| `ch09/docs/프롬프트비교_양식.md` | 판본 비교 기록의 양식 | 11-4 |
| `ch09/.env.example`, `.gitignore`, `requirements.txt`, `pytest.ini` | 설정 견본(값 없음), 커밋 제외 목록, 고정 판, 테스트 설정 | 0절 |
| `교수/` | 교수 시연 순서(`시연.md`), 판본 비교 기록의 예시 답안, 실제 호출의 실행 기록을 만드는 `make_run_record.py`. 학생용 키트 저장소에 넣지 않는다 | |

## 쓰는 순서 (내 PC. 자세한 설명은 학생용 강의안 0절과 11절)

가상 환경을 켠 터미널을 전제로 한다(부록 A-13).

```bash
git -C ~/kits-repo pull && cp -rn ~/kits-repo/Service_09장 ~/kits/   # 키트 받기(부록 A-12-3)
cd ~/llm-service-lab
cp -rn ~/kits/Service_09장/ch09 .
python -m pip install -r ch09/requirements.txt
cd ch09
cp -n .env.example .env                       # LLM_FAKE=1 상태로 시작
python -m pytest                              # 42 passed
python -m uvicorn api.app:app --port 8000     # 다른 터미널. 자동 문서 http://127.0.0.1:8000/docs
python -m eval.run_compare v1 v2 v3           # 판본 비교(모의 응답 재생) → results/비교표.md
python tools/check_secrets.py                 # KEY_CHECK_OK
```

포트는 API 8000이다(부록 A-16). 이 장의 API는 웹 화면을 함께 보내지 않는다. 요청은 `curl`로 보낸다.

## 모의 모드와 실제 호출

- `LLM_FAKE=1`(기본): API를 부르지 않는다. 요약 API는 공고의 칸을 규칙으로 옮긴 모의 요약을 내고, 판본 비교는 `eval/모의응답/`에 미리 적어 둔 응답을 재생한다. 모의 응답은 수업용으로 만든 예시이며 실제 모델의 출력이 아니다.
- `LLM_FAKE=0`: `.env`에 키(`ANTHROPIC_API_KEY`)를 넣은 뒤에만 쓴다. 키는 선택이다. 학생의 실행 상한은 `tools/first_call.py` 1회이다. 판본 비교의 실제 측정(호출 90회)은 교수가 `교수/make_run_record.py`로 하고, 그 기록을 키트 저장소의 `Service_09장_실행기록/`으로 배포한다.

## 자료를 바꿀 때

서비스 4의 자료를 공개 API로 받은 문서(후보: 고용24 직업정보)로 바꾸면 고칠 곳은 다음과 같다(2026-11-18, 바꾸지 않음).

| 고칠 곳 | 내용 |
|---|---|
| `eval/공고/*.txt`, `eval/정답.json` | 새 문서 10건과 정답(마감일 대신 새 필드) |
| `api/schema.py`의 `FIELDS`, `SUMMARY_SCHEMA`, `Summary` | 요약 필드 |
| `api/fake.py` | 새 문서의 칸 이름을 옮기는 규칙 |
| `prompts/v1~v3.md`, `eval/모의응답/v1~v3.json` | 새 문서에 맞춘 판본과 모의 응답 |
| `eval/grader.py` | `마감일` 항목을 새 필드의 판정으로 |
| `tests/test_api.py`, `test_grader.py`, `test_prompts.py`, `test_compare.py` | 필드 이름과 기대값 |

## 확인한 환경

- 2026-11-18: Windows 11 빌드 26300, Git Bash, Python 3.13.7, 위 `requirements.txt`의 판(새 가상 환경). `pytest` 42 passed, `first_call.py`(모의), uvicorn 8000의 `/api/health`, `/api/summary`(200, 캐시, 422, 404, `RATE_LIMIT_PER_MIN=2`의 429, `LLM_FAKE=0`·키 없음의 503), `run_compare`(v1 17/50, v2 42/50, v3 49/50), `cost_estimate.py`(v3 $6.23, v2 $4.89), `check_secrets.py`(OK와 `git add -f .env`의 FAIL), `교수/make_run_record.py`(`LLM_FAKE=1` 리허설).
- 확인하지 못함: 실제 API 호출(`LLM_FAKE=0`과 키), macOS에서의 실행.
