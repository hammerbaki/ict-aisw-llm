# Service_10장 키트: 검색 증강 생성(RAG)

「LLM 서비스 개발」 10장(학사 12주차, 서비스 4 「문서 요약과 질의응답」의 2/2)의 실습 재료다. 가상 문서 다섯 개를 근거로 답하는 질의응답(`python -m rag`)을 완성하고, 평가 문항 10개로 검색의 재현율@3을 잰다. 9장의 결과가 없어도 시작할 수 있다. API와 화면에는 붙이지 않는다.

## 들어 있는 것

| 경로 | 내용 | 학생이 고치는가 | 쓰는 절 |
|---|---|---|---|
| `ch10/rag/` | 색인, 검색, 답변, 측정 코드. 네 함수(`vector_search`, `recall_at_k`, `build_prompt`, `trim_history`)가 TODO다 | TODO 네 함수만 | 1~8절 |
| `ch10/rag/평가문항.csv` | 평가 문항 10개와 정답 절 | 고치지 않는다 | 8-5 |
| `ch10/rag/범위밖문항.csv` | 자료에 없는 질문 3개(기준값 정하기용) | 고치지 않는다 | 8-6 |
| `ch10/자료/` | 가상 문서 다섯 개(취업 지원 안내, 자기소개서 작성 가이드, 면접 준비 안내, 현장실습 운영 규정, 채용 공고 발췌) | 고치지 않는다 | 3-3 |
| `ch10/tests/rag/` | 고정 테스트 24개(대체 임베딩, 모의 LLM으로 돈다) | 고치지 않는다 | 0-2, 8-4 |
| `ch10/docs/요구사항명세서_양식.md` | 서비스 4의 질의응답 요구(EARS) 11개 | 복사해 「 」를 채운다 | 8-2 |
| `ch10/docs/검색평가_양식.md` | 검색 평가 보고 양식 | `검색평가.md`로 복사해 채운다 | 8-5~8-9 |
| `ch10/.env.example`, `.gitignore`, `requirements.txt`, `pytest.ini` | 설정 견본(값 없음), 제외 목록(`.env`, `rag/index/`), 고정 판, 테스트 설정 | | 0-2 |
| `시연기록/` | 교수 시연의 실행 기록(Ollama 임베딩 경로, 실제 모델의 답)이 올라올 자리. 지금은 안내 파일만 있다 | 읽기만 한다 | 2-3, 8-6 |
| `교수/` | 완성판 `rag/`, 검색평가 예시 답안, 시연 지시, 실행 기록을 만드는 `시연기록_만들기.sh`와 그 점검 결과, 숨은 지시가 든 가상 공고(`자료_실험/`). 학생용 키트 저장소에 넣지 않는다 | | |

## 쓰는 순서 (내 PC. 자세한 설명은 학생용 강의안 0절과 8절)

가상 환경을 켠 터미널을 전제로 한다(부록 A-13). Windows에서는 `PYTHONUTF8=1`을 등록해 둔다(부록 A-3-4).

```bash
git -C ~/kits-repo pull && cp -rn ~/kits-repo/Service_10장 ~/kits/   # 키트 받기(부록 A-12-3)
cd ~/llm-service-lab
cp -rn ~/kits/Service_10장/ch10 .
cd ch10
python -m pip install -r requirements.txt
cp -n .env.example .env          # LLM_FAKE=1
python -m pytest tests/rag       # 처음에는 16 failed, 8 passed가 정상이다
python -m rag index              # 청크 36개(대체 임베딩)
```

네 함수를 완성하면 `tests/rag`가 `24 passed`가 된다. `tests/` 아래 파일은 고치지 않는다.

## 환경 변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `EMBED_BACKEND` | `fallback` | `fallback`은 글자 n-gram 대체 구현이다. 누가 실행해도 같은 벡터가 나온다. `ollama`는 내 PC의 Ollama(선택, 부록 A-17)를 쓰고 연결할 수 없으면 오류를 낸다. `auto`는 Ollama를 먼저 시도한다(측정에는 쓰지 않는다) |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama 임베딩 모델 이름 |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 주소 |
| `CHUNK_MODE` | `heading` | `heading`(제목 단위) 또는 `size`(고정 길이) |
| `CHUNK_MAX_CHARS` | `500` | 청크 길이의 상한(글자) |
| `CHUNK_OVERLAP` | `0` | 겹치는 글자 수 |
| `CHUNK_ADD_TITLE` | `1` | 1이면 청크 앞에 「문서 제목 > 절 제목」을 붙여 임베딩 |
| `TOP_K` | `3` | 근거로 쓸 청크 수 |
| `SEARCH_METHOD` | `vector` | `vector`, `keyword`, `hybrid` |
| `RAG_MIN_SCORE` | 대체 0.18, Ollama 0.50 | 1위 유사도가 이보다 낮으면 「자료에 없다」. Ollama 값은 자리만 잡은 값이다. 청킹 설정을 바꾸면 `calibrate`로 다시 정한다 |
| `MAX_TURNS` | `4` | LLM에 보낼 최근 왕복 수 |
| `LLM_FAKE` | `.env`의 `1` | `1`이면 API를 부르지 않는 모의 모드 |
| `LLM_MODEL` | `.env`의 `claude-haiku-5-5` | 실제 호출에 쓸 모델 이름. 코드에 적지 않는다 |

## 자료를 바꿀 때

서비스 4의 자료를 공개 API로 받은 문서(후보: 고용24 직업정보)로 바꾸면 고칠 곳은 다음과 같다(2026-11-18, 바꾸지 않음).

| 고칠 곳 | 내용 |
|---|---|
| `자료/*.md` | 받은 문서를 마크다운으로 바꾼 것(절 제목 `##`이 청킹의 경계가 된다) |
| `rag/평가문항.csv`, `rag/범위밖문항.csv` | 새 질문과 정답 절(`문서이름#절 제목`) |
| `rag/config.py`의 `NO_ANSWER`, `DEFAULT_MIN_SCORE` | 거절 문장(취업지원실 안내)과 `calibrate`로 다시 잰 기준값 |
| `tests/rag/test_rag_search.py`, `test_rag_eval.py`, `test_rag_answer.py` | 키트 자료에 기대는 테스트(1위 절, 재현율, 거절 문장) |
| `docs/요구사항명세서_양식.md` | 서비스 설명과 자료의 줄 |
| `교수/시연기록_만들기.sh`, `교수/정답_검색평가.md` | 질문 문장과 예시 답안 |

## 확인한 것과 확인하지 못한 것

- 확인(2026-11-18): Windows 11 빌드 26300, Git Bash, Python 3.13.7, 위 `requirements.txt`의 판(새 가상 환경). `교수/`를 뺀 키트를 복사해 받는 흐름, 학생판 `16 failed, 8 passed`, 완성판 세 파일을 넣은 뒤 `24 passed`와 `diff -r -x __pycache__`, `python -m rag index·search·prompt·ask·eval·calibrate`, 고정 길이 200자의 회귀(4번 문항)와 `CHUNK_OVERLAP=50`의 해결, `.gitignore`의 `rag/index/`, `교수/시연기록_만들기.sh`(`EMBED_BACKEND=fallback`, 모의 모드, 약 82초. 끝난 뒤 `자료/`가 다섯 개로 돌아오고 기본 색인이 다시 만들어짐).
- 자료 머리말의 장 번호를 옛 번호에서 새 번호(10장)로 고쳤다. 대체 임베딩의 값이 조금 바뀌었다(예: 고정 길이 200자에서 면접 안내 머리말의 유사도 0.3041 → 0.3070, 겹침 50에서 4번 문항의 1위가 「비대면 면접 환경」에서 「머리말」로 바뀌고 2·3위가 그 절). 재현율, 기준값 후보, 회귀와 해결의 결론은 같다.
- 확인하지 못함: Ollama 임베딩 경로(집필 PC에 Ollama가 없다), 실제 LLM API 호출(`LLM_FAKE=0`), Claude Code가 네 함수를 구현하는 대화, macOS에서의 실행.
