# 기준 산출물 (7장을 마치지 못한 학습자용)

8장은 7장에서 조립한 하네스가 저장소에 있다고 보고 루프를 그 위에서 돌린다. 하네스가 없는 학습자는 `jobprep/` 안의 파일을 저장소에 복사해 출발점을 맞춘다(강의안 0-2). 7장을 마친 학습자는 자기 파일을 쓴다(`cp -rn`은 이미 있는 파일을 덮어쓰지 않는다).

| 파일 | 원래 만드는 장 | 출처 (2026-11-14 정합 작업에서 복사, 2026-11-17 내 PC 기준 개편본으로 다시 복사) |
|---|---|---|
| `CLAUDE.md`, `.claude/settings.json`, `.claude/agents/reviewer.md` | 7장(조립) | 7장 키트의 `조립/`. 훅 셋(PreToolUse `protect.sh`, PostToolUse `run_tests.sh`, Stop `stop_gate.sh`)을 공유 설정에 둔 판과 검토 규칙 RV1~RV8 |
| `.claude/hooks/` | 6장(훅) | 7장 키트의 `기준산출물/.claude/hooks/`(`protect.sh`, `protected.txt`, `run_tests.sh`, `stop_gate.sh`, `check_hooks.sh`, `samples/`) |
| `.claude/rules/`, `docs/운영/저장소규약.md` | 3장(팀 규칙) | 7장 키트의 `기준산출물/` |
| `plugins/jobprep-ops/` | 4장(스킬과 플러그인) | 4장 키트의 `예비/`(`SKILL.md`, `README_plugin.md`, `plugin.json`)와 `재료/incident-report/`(참조 파일, UTF-8로 출력하는 스크립트 둘) |
| `plugins/jobprep-harness/`, `.claude-plugin/marketplace.json` | 7장(하네스 플러그인) | 7장 키트의 `플러그인/`(마켓플레이스 `jobprep-team`에 두 플러그인) |
| `.mcp.json`, `mcp/ops_server.py` | 5장(MCP) | 7장 키트의 `기준산출물/`(서버 `jobprep-ops`, 도구 `error_summary`, `status_counts`, `slow_requests`, `read_log`). `mcp==2.3.0`이 필요하다. 서버는 `"command": "python"`으로 띄우므로 Claude Code는 가상 환경을 켠 터미널의 저장소 맨 위에서 연다 |
| `tests/.baseline.json`, `tools/test_guard.py` | 2장(테스트 동결) | 7장 키트의 `기준산출물/`(새 형식, 파일 11개) |
| `docs/운영/하네스설계서.md` | 7장(하네스 설계서) | 7장 키트의 교수용 견본 |

동결 기록은 2장을 마친 저장소(테스트 세 파일 `test_closing_within.py`, `test_summary_limits.py`, `test_ask_limits.py`와 마커를 등록한 `pytest.ini`)를 기준으로 하였다. 2장을 하지 않은 저장소에 복사하면 `python tools/test_guard.py check`가 그 파일들을 「삭제」와 「수정」으로 알리고, 편집 뒤 테스트 훅(`run_tests.sh`)이 매번 동결 검사 실패를 보고한다(`bash .claude/hooks/check_hooks.sh`의 결과가 「통과 17, 실패 1」이 된다). 그때는 6장 0-2처럼 사람이 확인한 뒤 `python tools/test_guard.py freeze --update`로 다시 동결한다.

이 폴더에는 `.claude/`와 `CLAUDE.md`가 들어 있다. 키트 폴더 안에서 `claude`를 띄우면 이 파일들이 읽힐 수 있으므로, Claude Code는 언제나 저장소 폴더에서 띄운다.

가상 환경 규칙(부록 A-9): `CLAUDE.md`와 `.claude/settings.json`은 가상 환경을 켠 뒤 `python`으로 부르는 꼴만 쓴다(`.venv/bin/python …` 같은 경로 호출의 허용 규칙은 뺐다. Bash 규칙은 명령의 글자에 맞추므로 3장 판정 사례 13번처럼 경로 호출은 허용 규칙에 맞지 않는다). 가상 환경을 켜지 않고 도는 훅은 `.venv/Scripts/python.exe`를 먼저, 없으면 `.venv/bin/python`을 찾는다.
