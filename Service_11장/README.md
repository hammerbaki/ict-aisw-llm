# Service_11장 키트: 검색 증강 생성(RAG) 기능의 구현

「LLM 서비스 개발」 11장(학사 13주차)의 실습 재료다. 10장의 `jobprep/api/`(공고 요약 API)에 취업 자료 질의응답 기능(`POST /api/ask`)과 화면(`web/ask.html`)을 붙이고, 평가 문항 10개로 검색의 재현율@3을 잰다.

## 들어 있는 것

| 경로 | 내용 | 학생이 고치는가 |
|---|---|---|
| `jobprep/rag/` | 색인, 검색, 답변, 측정 코드. 네 함수(`vector_search`, `recall_at_k`, `build_prompt`, `trim_history`)가 TODO다 | TODO 네 함수만 |
| `jobprep/rag/평가문항.csv` | 평가 문항 10개와 정답 절 | 고치지 않는다 |
| `jobprep/rag/범위밖문항.csv` | 자료에 없는 질문 3개(기준값 정하기용) | 고치지 않는다 |
| `jobprep/api/ask_route.py` | `POST /api/ask` 라우터 | 고치지 않는다 |
| `jobprep/web/ask.html`, `ask.js`, `ask.css` | 질의응답 화면(근거 표시) | 디자인 토큰에 맞추어 고쳐도 된다 |
| `jobprep/자료/` | 가상 문서 다섯 개(취업 지원 안내, 자기소개서 작성 가이드, 면접 준비 안내, 현장실습 운영 규정, 채용 공고 발췌) | 고치지 않는다 |
| `jobprep/자료_실험/주입_공고.md` | 숨은 지시가 든 가상 공고(간접 프롬프트 주입 실험용). `자료/`에 넣어 두지 않는다 | 고치지 않는다 |
| `jobprep/tests/rag/` | 고정 테스트 29개(대체 임베딩, 모의 LLM으로 돈다) | 고치지 않는다 |
| `jobprep/docs/RAG요구_양식.md` | 명세서에 붙일 RAG 요구(EARS) 13개 | 「 」를 채워 명세서에 붙인다 |
| `jobprep/docs/검색평가_양식.md` | 검색 평가 보고 양식 | `검색평가.md`로 복사해 채운다 |
| `기준산출물/jobprep/` | 10장 산출물이 없는 학생을 위한 견본. 10장 키트 `jobprep/`의 완성 상태 전체(`api/`, `prompts/`, `eval/`, `tools/`, `tests/` 42개, `pytest.ini`, `requirements.txt`, `.env.example`, `.gitignore`에 `rag/index/` 한 줄을 더함), 10장 기준 산출물의 웹에 10장 정답(`detail.html`, `js/summary.js`)을 덮은 웹, 10장 교수 예시의 `docs/프롬프트비교.md`, 6장 정본 명세서(REQ-001~023)에 10장 변경을 더한 명세서 견본 v5, `CLAUDE.md`(2026-11-14 정합 작업에서 다시 복사) | 받아서 쓴다 |
| `시연기록/` | 교수 시연의 실행 기록(Ollama 임베딩 경로, 실제 모델의 답). 교수가 수업 전에 키트 저장소의 이 폴더에 `11장_시연기록.md`를 올린다. 지금은 안내 파일만 있다 | 읽기만 한다 |
| `교수/` | 완성판 코드, 정답 예시, 시연 지시, 실행 기록을 만드는 `시연기록_만들기.sh`와 그 점검 결과(`시연기록_예시_fallback.md`). 학생용 키트 저장소에 넣지 않는다. 키트의 테스트는 `교수/`를 읽지 않으므로 `교수/`가 없어도 29개가 모두 돈다 | |
| `requirements.txt` | 고정한 패키지 판 | |

## 쓰는 순서 (내 PC. 자세한 설명은 학생용 강의안 0절과 12절)

가상 환경을 켠 터미널(Windows Git Bash `source ~/llm-service-lab/.venv/Scripts/activate`, macOS `source ~/llm-service-lab/.venv/bin/activate`)을 전제로 한다(부록 A-13). Windows에서는 한글 출력이 깨지지 않게 `export PYTHONUTF8=1`도 한 번 해 둔다(부록 A).

```bash
git -C ~/kits-repo pull && mkdir -p ~/kits && cp -rn ~/kits-repo/Service_11장 ~/kits/   # 키트 받기(부록 A-12-3)
cd ~/llm-service-lab
ls jobprep/api/app.py || cp -rn ~/kits/Service_11장/기준산출물/jobprep/. jobprep/   # 10장 산출물이 없을 때만
cp -rn ~/kits/Service_11장/jobprep/. jobprep/                                     # 키트를 jobprep에 합친다(있는 파일은 덮지 않는다)
python -m pip install -r ~/kits/Service_11장/requirements.txt
cd jobprep
cp -n .env.example .env          # 10장의 .env가 있으면 그대로 둔다(LLM_FAKE=1)
python -m pytest tests/rag       # 처음에는 19 failed, 10 passed가 정상이다(아래)
python -m rag index              # 청크 36개(대체 임베딩)
python -m uvicorn api.app:app --port 8000   # 라우터 두 줄을 더한 뒤. 화면은 http://localhost:8000/ask.html
```

API에 붙이는 것은 `api/app.py`에 두 줄이다(`from api.ask_route import router as ask_router`, 그리고 `WEB_DIR` 줄 위에 `app.include_router(ask_router)`). 화면은 10장처럼 API 서버의 같은 출처(`http://localhost:8000/ask.html`)에서 연다. 웹을 `python -m http.server 8100`으로 따로 띄우면 `ask.js`의 상대 주소 `/api/ask`가 8100으로 가서 501이 된다(10장 핵심 실습의 해결 과제와 같은 원인).

## 처음 실행할 때 기대하는 화면

TODO 네 함수가 비어 있으므로 처음에는 다음과 같이 실패한다(2026-11-14, 대체 임베딩, 모의 모드).

```text
python -m pytest tests/rag   → 19 failed, 10 passed
python -m pytest             → 19 failed, 52 passed   (10장 테스트 42개 포함)
```

네 함수를 완성하면 `tests/rag`가 `29 passed`, 전체가 `71 passed`(10장 테스트 42개 포함)가 된다. 기준 산출물이 10장 키트의 테스트를 모두 담으므로 10장을 끝낸 학생과 수가 같다. `tests/` 아래 파일은 고치지 않는다.

## 환경 변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `EMBED_BACKEND` | `fallback` | `fallback`(기본)은 글자 n-gram 대체 구현이다. 누가 실행해도 같은 벡터가 나오므로 재현율과 기준값이 학생마다 같다. `ollama`는 내 PC에 설치한 Ollama(선택, 부록 A-17)를 쓰고, 연결할 수 없으면 오류를 낸다. `auto`는 Ollama를 먼저 시도하고 안 되면 대체 구현으로 돈다(설치 여부에 따라 결과가 달라지므로 측정에는 쓰지 않는다). 2026-11-17에 기본값을 `auto`에서 `fallback`으로 바꾸었다(사용자 결정 11 Q5) |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama 임베딩 모델 이름(수업에서 안내한 값) |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 주소 |
| `CHUNK_MODE` | `heading` | `heading`(제목 단위) 또는 `size`(고정 길이) |
| `CHUNK_MAX_CHARS` | `500` | 청크 길이의 상한(글자) |
| `CHUNK_OVERLAP` | `0` | 겹치는 글자 수 |
| `CHUNK_ADD_TITLE` | `1` | 1이면 청크 앞에 「문서 제목 > 절 제목」을 붙여 임베딩 |
| `TOP_K` | `3` | 근거로 쓸 청크 수 |
| `SEARCH_METHOD` | `vector` | `vector`, `keyword`, `hybrid` |
| `RAG_MIN_SCORE` | 대체 0.18, Ollama 0.50 | 1위 유사도가 이보다 낮으면 「자료에 없다」. Ollama 값은 자리만 잡은 값이므로 그 모델로 `calibrate`를 돌려 다시 정한다. 청킹 설정을 바꾸어도 다시 정한다(강의안 12-10) |
| `MAX_TURNS` | `4` | LLM에 보낼 최근 왕복 수 |
| `LLM_FAKE` | (없음) | `1`이면 API를 부르지 않는 모의 모드. `jobprep/.env`의 값을 `python -m rag`와 API 서버가 함께 읽는다 |
| `LLM_MODEL` | (없음) | 실제 호출에 쓸 모델 이름. 코드에 적지 않는다 |

## 확인한 것과 확인하지 못한 것

- 확인(2026-11-14): Windows 11, Python 3.13.7, 위 `requirements.txt`의 판, 대체 임베딩과 `LLM_FAKE=1`에서 학생판 `19 failed, 10 passed`, 완성판 `29 passed`(기준 산출물과 합쳐 `71 passed`), `python -m rag index·search·prompt·ask·eval·calibrate`, `uvicorn api.app:app`과 `POST /api/ask`, 브라우저의 `ask.html`.
- 확인(2026-11-15): `교수/시연기록_만들기.sh`를 대체 임베딩·모의 모드로 실행해 기록 파일이 만들어지고, 끝난 뒤 `자료/`가 다섯 개로 돌아오고 기본 색인(청크 36개)이 다시 만들어지는 것.
- 확인(2026-11-17, 결정 11 개편): Windows 11 빌드 26300, Git Bash, Python 3.13.7. `교수/`를 뺀 키트를 시험용 키트 저장소로 클론해 받는 흐름, `EMBED_BACKEND`의 새 기본값(`fallback`)으로 환경 변수 없이 강의안의 숫자가 나오는 것, 고정 길이 200자의 회귀(4번 문항)와 `CHUNK_OVERLAP=50`의 해결, `uvicorn` 8000과 `ask.html`. 기준 산출물의 `api/app.py`, `api/schema.py`, `.env.example`, `docs/프롬프트비교_양식.md`, `docs/프롬프트비교.md`를 10장 키트의 개편본(2026-11-17)에 맞추었다.
- 확인하지 못함: Ollama 임베딩 경로(집필한 PC에 Ollama가 없었다), 실제 LLM API 호출(`--real`), macOS에서의 실행.
