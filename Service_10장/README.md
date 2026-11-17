# Service_10장: LLM 기능의 통합 키트

「LLM 서비스 개발」 10장(학사 12주차)의 실습 재료이다. 공고 요약 API(FastAPI)를 만들어 9장의 웹에 붙이고, 프롬프트 판본 세 개를 평가 문항 10개로 비교해 하나를 채택한다. 모든 코드는 모의 모드(`LLM_FAKE=1`)에서 키 없이 끝까지 돈다.

## 들어 있는 것

| 경로 | 내용 |
|---|---|
| `jobprep/api/` | 요약 API. `app.py`(FastAPI), `llm.py`(호출을 한 곳에 모음, 모의 모드), `schema.py`(요약 형식), `prompts.py`(판본 파일 읽기), `fake.py`(모의 요약기) |
| `jobprep/prompts/` | 프롬프트 판본 `v1.md`(기준선), `v2.md`(규칙과 형식), `v3.md`(v2 + 예시 두 건) |
| `jobprep/eval/` | 평가 문항(가상 공고 10건 `공고/`, 정답 `정답.json`), 채점기 `grader.py`, 판본 비교 실행기 `run_compare.py`, 모의 응답 `모의응답/` |
| `jobprep/tools/` | `first_call.py`(요청 한 번의 구조 보기), `count_tokens.py`(토큰 세기), `cost_estimate.py`(월 비용 어림), `check_secrets.py`(키 노출 검사) |
| `jobprep/tests/` | pytest 테스트 42개. 모의 모드에서 모두 통과한다 |
| `jobprep/docs/프롬프트비교_양식.md` | 판본 비교 기록의 양식 |
| `jobprep/.env.example`, `.gitignore`, `requirements.txt`, `pytest.ini` | 설정 견본, 커밋 제외 목록, 고정 버전 |
| `기준산출물/jobprep/web/` | 9장 키트의 정답 웹(`Service_09장/교수/web/`, 2026-11-14 복사)에 상세 화면의 「AI 요약」 영역(`#summary-btn`, `#summary-status`, `#summary`)만 더한 것. 9장 결과가 없을 때만 쓴다 |
| `교수/` | 정답 `web/js/summary.js`와 `web/detail.html`, 판본 비교 기록 예시, 시연 순서, 교수 시연의 실행 기록을 만드는 `make_run_record.py`. 학생용 키트 저장소에 넣지 않는다 |

## 쓰는 순서 (내 PC. 자세한 설명은 학생용 강의안 0절과 11절)

가상 환경을 켠 터미널(Windows Git Bash `source ~/llm-service-lab/.venv/Scripts/activate`, macOS `source ~/llm-service-lab/.venv/bin/activate`)을 전제로 한다(부록 A-13). 가상 환경이 아직 없으면 저장소 맨 위에서 `python -m venv .venv`로 만든 뒤 켠다.

```bash
git -C ~/kits-repo pull && mkdir -p ~/kits && cp -rn ~/kits-repo/Service_10장 ~/kits/   # 키트 받기(부록 A-12-3)
cd ~/llm-service-lab
ls jobprep/web || cp -rn ~/kits/Service_10장/기준산출물/jobprep/web jobprep/   # 9장 웹이 없을 때만
cp -rn ~/kits/Service_10장/jobprep/. jobprep/            # 키트를 jobprep에 합친다(있는 파일은 덮지 않는다)
python -m pip install -r jobprep/requirements.txt
cd jobprep
cp -n .env.example .env                                    # LLM_FAKE=1 상태로 시작
python -m pytest                                           # 42 passed
python -m eval.run_compare v1 v2 v3                        # 판본 비교(모의 응답 재생) → results/비교표.md
python -m uvicorn api.app:app --port 8000                  # http://localhost:8000/detail.html?id=JOB-003
python tools/check_secrets.py                              # KEY_CHECK_OK
```

`.env`가 이미 있는 9장 이후의 폴더에서는 `cp -n`이 덮어쓰지 않는다. 그때는 `.env.example`의 변수(`LLM_FAKE`, `LLM_MODEL`, `LLM_EFFORT`, `PROMPT_VERSION`, `RATE_LIMIT_PER_MIN`)가 `.env`에 있는지 확인한다.

포트는 API 8000, 웹 8100으로 고정한다(부록 A-16). API 서버가 `web/`을 같은 출처(`http://localhost:8000/`)에서 함께 보내므로 웹을 따로 띄우지 않는다. 웹을 `python -m http.server 8100`으로 따로 띄우면 상대 주소 `/api/summary`가 8100으로 가서 501이 된다(학생용 11-6, 핵심 실습의 해결 과제). `WEB_ORIGIN`(기본 `http://localhost:8100`)은 웹을 다른 출처에서 열어 API의 전체 주소로 부를 때만 쓰인다.

Windows의 Git Bash에서 파이썬 출력을 `|`로 다른 명령에 넘기면 한글이 깨질 수 있다. 그때는 명령 앞에 `PYTHONUTF8=1`을 붙인다(부록 A).

## 모의 모드와 실제 호출

- `LLM_FAKE=1`(기본): API를 부르지 않는다. 요약 API는 공고의 칸을 규칙으로 옮긴 모의 요약을 내고, 판본 비교는 `eval/모의응답/`에 미리 적어 둔 응답을 재생한다. 모의 응답은 수업용으로 만든 예시이며 실제 모델의 출력이 아니다.
- `LLM_FAKE=0`: `.env`에 키(`ANTHROPIC_API_KEY`)를 넣은 뒤에만 쓴다. 키는 선택이다(사용자 결정 11, 2026-11-16). 직접 실제 호출을 해 볼 학생만 각자 Claude Console에서 발급하고(부록 A-14), 이 장의 실행 상한(`tools/first_call.py` 1회)만 실제로 부른다. 판본 비교의 실제 측정(호출 90회)은 교수 시연으로 하고, 학생은 교수가 키트 저장소에 올리는 실행 기록(`Service_10장_실행기록/`)으로 읽는다. 모델은 `LLM_MODEL`(기본 `claude-haiku-5-5`, 2026-11 기준)로 정한다. 실제 호출은 집필 시점에 키가 없어 실행해 보지 못했고, SDK 2.8.0의 시그니처와 공식 문서로 대조하였다.

## 교수 전용 폴더

`교수/`(정답 `web/js/summary.js`와 `web/detail.html`, 판본 비교 기록 예시, 시연 순서, 실행 기록을 만드는 `make_run_record.py`)는 학생용 키트 저장소에 넣지 않는다. 키트의 테스트는 `교수/`를 읽지 않으므로 `교수/`가 없어도 42개가 모두 돈다.

## 확인한 환경

- 2026-11-14: Windows 11, Python 3.13.7, 위 `requirements.txt`의 버전. `pytest` 42 passed, 판본 비교(모의) v1 17/50, v2 42/50, v3 49/50.
- 2026-11-17(결정 11 개편): Windows 11 Git Bash, Python 3.13.7. 키트 저장소를 클론해(줄 끝 CRLF로 꺼내짐) 받는 흐름, 가상 환경 켜기, `pytest`, 판본 비교, uvicorn 8000, `http.server` 8100의 501과 같은 출처 해결을 다시 실행하였다.
