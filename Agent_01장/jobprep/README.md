# jobprep: 취업 준비 지원 서비스 (기준 저장소)

`jobprep`은 전문대학 2학년 취업 준비생을 위한 서비스이다. 채용 공고를 모아 보고, 관심 공고를 표시하고, 공고를 LLM으로 요약하고, 학과 취업 자료에 근거해 질문에 답한다. 「LLM 서비스 개발」의 여러 단원(공고 모아보기, API 서버, 문서 요약, 질의응답)에서 다룬 기능을 한 서비스로 묶은 것이며, 「AI에이전트 기획 및 개발」은 이 저장소를 운영 대상으로 삼아 학기 내내 테스트, 하네스, 루프, 멀티 에이전트, 보안, 평가, CI를 더한다.

공고 30건, 기업, 취업 자료, 운영 기록은 모두 **실습용 가상 자료**이다. 기업 이름은 지어낸 것이며 실제 기업과 같은 이름이 있더라도 관계가 없다.

## 구조

```
jobprep/
├── api/                 FastAPI 백엔드
│   ├── main.py          엔드포인트와 기록 설정 (진입점: api.main:app)
│   ├── jobs.py          공고 읽기와 고르기
│   ├── summary.py       공고 요약과 요약 구조 검사
│   ├── ask.py           취업 자료 질의응답(검색 → 근거 판정 → 생성)
│   └── llm.py           LLM 호출을 한곳에 모은 모듈(모의 모드 포함)
├── rag/                 검색: chunker.py(청킹), embedder.py(임베딩), search.py(검색), index.py(색인)
│   └── 평가문항.csv     검색 재현율 평가 문항 10개
├── prompts/             프롬프트 판본(summary_v1, summary_v2, ask_v1)
├── web/                 정적 웹(빌드 도구 없음): 공고 목록, 공고 상세와 요약, 질의응답
├── data/
│   ├── jobs.json        가상 채용 공고 30건
│   └── 자료/            가상 학과 취업 지원 문서 6편
├── docs/
│   ├── 요구사항명세서.md EARS로 쓴 요구사항(REQ-ID, 상태, 테스트)
│   └── 운영/            운영 문서를 두는 곳(1장부터 채운다)
├── logs/                운영 기록 견본(가상, 1주일분)
├── evals/               회귀 평가를 두는 곳(12장에서 채운다)
├── tests/               pytest 테스트
├── requirements.txt     직접 쓰는 패키지와 고정한 버전
├── .env.example         환경 변수 견본(실제 값은 .env에, .env는 저장소에 올리지 않는다)
└── pytest.ini
```

## 실행

명령은 저장소 폴더(`jobprep/`)에서 실행한다. 파이썬 3.12 이상이 필요하다. 이 과목은 내 PC에서 실습한다. 터미널은 Windows에서는 VS Code의 Git Bash, macOS에서는 기본 셸이다(부록 A-4).

### 1. 가상 환경과 설치

가상 환경은 저장소 맨 위에 하나(`.venv`) 만들고, 터미널을 열 때마다 먼저 켠다. 켠 뒤로는 `python`, `python -m pytest`, `python -m pip`로 부른다(부록 A-9). Git Bash에는 `python3`이 없다.

```bash
python -m venv .venv               # macOS: python3 -m venv .venv
source .venv/Scripts/activate      # macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
```

가상 환경을 켜지 않은 채 도는 훅과 스크립트(6장 이후)는 `.venv/Scripts/python.exe`가 있으면 그것을, 없으면 `.venv/bin/python`을 쓴다(부록 A-9-2).

### 2. 테스트

```bash
python -m pytest -q
```

테스트는 `tests/conftest.py`가 모의 모드(`LLM_FAKE=1`)와 대체 임베딩을 켜고 돌린다. API 키와 Ollama가 없어도 모두 통과한다(`43 passed`).

### 3. API 서버

포트는 API 8000, 웹 8100으로 고정한다(부록 A-10).

```bash
LLM_FAKE=1 uvicorn api.main:app --port 8000
```

서버가 뜨면 <http://127.0.0.1:8000/docs>에서 엔드포인트를 시험할 수 있다. 다른 터미널에서 요청을 보낸다.

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/jobs/1
curl -X POST http://127.0.0.1:8000/api/summary -H "Content-Type: application/json" \
     -d '{"text": "[주요 업무]\n- 화면을 만든다\n[유의 사항]\n- 접수 마감: 2027-10-01 18:00"}'
```

8000번을 이미 다른 프로그램이 쓰고 있으면 `netstat -ano | findstr :8000`(macOS는 `lsof -nP -iTCP:8000 -sTCP:LISTEN`)으로 찾아 멈추거나 다른 번호를 쓴다(부록 A-10-2).

### 4. 웹

API 서버를 띄운 채 터미널을 하나 더 열고(가상 환경을 켠 뒤) 실행한다.

```bash
python -m http.server 8100 --bind 127.0.0.1 --directory web
```

<http://localhost:8100/>를 연다. 웹은 같은 컴퓨터의 8000번 포트에 있는 API를 부른다(`web/js/common.js`의 `API_BASE`). API를 다른 번호로 띄웠으면 주소 끝에 `?api=번호`를 붙인다. 관심 공고는 브라우저의 localStorage에만 저장된다.

### 5. 검색 색인

질의응답을 처음 부를 때 `rag/index.json`이 없으면 자동으로 만든다. 자료 문서를 고친 뒤에도 자동으로 다시 만든다. 직접 만들거나 재현율을 재려면 다음을 실행한다.

```bash
python -m rag.index
python -m rag.index eval rag/평가문항.csv
```

내 PC에 Ollama를 설치했으면 Ollama의 임베딩을, 없으면 대체 구현(글자 bigram)을 쓴다. 대체 구현이 기본이며 Ollama는 선택이다. 어느 쪽을 썼는지는 `python -m rag.index`의 출력이나 색인 파일의 `backend` 값으로 확인한다. 색인과 질문은 같은 방식으로 임베딩되며, 방식이 바뀌면 색인을 자동으로 다시 만든다. `EMBED_BACKEND=auto`에서 Ollama가 없으면 첫 질의응답이 연결을 3초 기다린 뒤 대체 구현으로 넘어간다. 기다림이 싫으면 `.env`에 `EMBED_BACKEND=fallback`을 둔다.

Windows의 Git Bash에서 파이썬의 한글 출력을 파이프(`|`)로 넘기면 글자가 깨질 수 있다. 부록 A-4-4의 `PYTHONUTF8=1`을 한 번 등록해 둔다.

### 6. 실제 LLM 호출 (선택)

실습은 모의 모드가 기본이며, 키 없이 모든 장이 끝까지 돈다. 실제로 불러 보려면 각자 Claude Console에서 API 키를 발급한다(선택, 부록 A-2-3). 모의 모드로 기능을 확인한 뒤 `.env`에서 `LLM_FAKE=0`으로 바꾸고, 그 키를 `ANTHROPIC_API_KEY`에, 수업에서 정한 모델 이름을 `LLM_MODEL`에 넣은 뒤 서버를 다시 띄운다. 키는 저장소의 `.env`에만 두고 `web/`의 코드나 저장소의 다른 파일에 넣지 않는다. 키가 새어 나갔으면 Console에서 바로 폐기한다(부록 A-11-3). Claude Code의 구독 로그인은 이 키를 대신하지 않는다.

## 환경 변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `LLM_FAKE` | `0` | `1`이면 LLM을 부르지 않고 모의 응답을 쓴다 |
| `LLM_MODEL` | (없음) | 실제 호출에 쓸 모델 이름 |
| `ANTHROPIC_API_KEY` | (없음) | 실제 호출에 쓸 API 키 |
| `PROMPT_SUMMARY`, `PROMPT_ASK` | `summary_v1`, `ask_v1` | 쓸 프롬프트 판본(`prompts/`의 파일 이름) |
| `EMBED_BACKEND` | `auto` | `auto`(Ollama가 있으면 쓰고 없으면 대체 구현), `ollama`, `fallback` |
| `OLLAMA_URL`, `EMBED_MODEL` | `http://localhost:11434`, `nomic-embed-text` | Ollama 임베딩 설정 |
| `RAG_INDEX_PATH` | `rag/index.json` | 색인 파일 위치 |
| `ASK_MIN_SCORE` | 임베딩별 기본값(ollama 0.5, fallback 0.3) | 근거로 인정할 최소 유사도 |
| `LOG_DIR` | (없음) | 정하면 그 폴더에 access.log, error.log, llm.log를 남긴다 |

## API

| 방법과 경로 | 하는 일 | 관련 요구 |
|---|---|---|
| `GET /api/health` | 서버 상태, 모의 모드 여부, 공고 수 | REQ-OPS-01 |
| `GET /api/jobs?field=&q=` | 공고 목록(마감일 순, 본문 제외, `days_left` 포함) | REQ-JOB-01~03, 05 |
| `GET /api/jobs/{id}` | 공고 상세. 없으면 404 | REQ-JOB-04 |
| `POST /api/summary` | `{"text"}` → `duties`, `qualifications`, `deadline`, `cautions`, `prompt_version`, `model` | REQ-SUM-01~04 |
| `POST /api/ask` | `{"question"}` → `answer`, `sources`, `prompt_version`, `model` | REQ-ASK-01~05 |

요구사항명세서에는 아직 구현하지 않은 요구가 있다(상태가 「미구현」인 것). 이 요구는 「AI에이전트 기획 및 개발」 2장에서 테스트를 먼저 쓰고 구현한다.
