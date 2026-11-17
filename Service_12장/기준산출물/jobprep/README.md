# jobprep 기준 산출물 (12장)

앞 장의 산출물이 없는 학습자가 12장을 진행하기 위한 견본이다. 11장 키트의 완성 상태(11장 기준 산출물 = 10장 키트의 완성 상태와 9·10장의 웹, 11장 학생판 키트, 11장 완성판 코드)를 복사하고, 12장 0-3절의 확장을 마친 판이다.

- `api/llm.py`: 10장의 `complete()`에 대화 이력(`messages`), 용도(`purpose`), 호출 기록(`LLM_LOG_PATH`), 모의 지연(`LLM_FAKE_LATENCY`), 모의 실패(`LLM_FAKE_FAIL`)를 더하였다. 10장의 호출부는 그대로 돈다.
- `rag/llm.py`: 질의응답의 호출도 `api/llm.py`의 `complete()`를 지나 기록에 남게 하였다(`purpose="ask"`).
- `tests/conftest.py`: 테스트의 호출 기록을 임시 파일로 보낸다.
- `docs/요구사항명세서.md`: 7장 정본 v2에 10장(v5)과 11장(v6)의 변경을 더한 견본. `docs/설계/`는 8장 정답의 화면 명세, 디자인 토큰, 접근성 점검이다. `docs/추적표.md`는 9장 기준 산출물의 추적표(6장에서 시작, 8장까지 채움), `docs/인수조건.md`는 9장의 인수 조건 견본이다.
- `.gitignore`: `rag/index/`, `api/logs/`, `.claude/worktrees/`를 더하였다.

```bash
source ~/llm-service-lab/.venv/Scripts/activate     # macOS: source ~/llm-service-lab/.venv/bin/activate
cd ~/llm-service-lab/jobprep
python -m pip install -r requirements.txt
python -m pytest -q
EMBED_BACKEND=fallback python -m rag index
python -m uvicorn api.app:app --port 8000
```

브라우저에서 `http://localhost:8000/`을 연다. 웹과 API를 이 서버 하나가 같은 출처에서 보낸다(10장). 포트는 부록 A-16을 따른다.
