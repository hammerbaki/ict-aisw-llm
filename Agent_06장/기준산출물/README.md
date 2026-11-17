# 기준 산출물 (2~5장을 마치지 못한 학생용)

6장은 2~5장의 결과(동결 기록, 팀 규칙과 권한 설정, MCP 연결)가 저장소에 있다고 보고 진행한다. 그 결과가 없는 학생은 아래 파일을 저장소에 복사해 출발점을 맞춘다. 앞 장을 마친 학생은 이 폴더를 쓰지 않는다. 모두 간단한 견본이며 각 장의 완성본이 아니다.

| 파일 | 원래 만드는 장 | 6장에서 쓰는 곳 |
|---|---|---|
| `tests/.baseline.json` | 2장(테스트 동결) | protect.sh가 이 기록의 `files` 목록을 「동결된 파일」로 보고 편집을 막는다. 기준 저장소에 2장 키트의 `pytest.ini`, 검사기, 정답(`교수/정답/tests`, `교수/정답/api`)을 넣은 저장소를 2장의 `test_guard.py freeze`로 동결한 기록이다(새 형식 `version`, `frozen_at`, `files`. 파일 11개: `tests/` 9개, `pytest.ini`, 검사기) |
| `tools/test_guard.py` | 2장(동결 검사기) | run_tests.sh가 편집 뒤에 `check`를 돌린다. 2장 키트 `도구/test_guard.py`의 사본이다 |
| `CLAUDE.md` | 3장(팀 규칙) | 1절의 지시와 강제 비교, 검토자의 검토 규칙 RV1~RV6의 근거 |
| `.claude/settings.json` | 3장(권한 규칙) | 훅 설정을 더할 바탕. `Read(./.env)` 거부 규칙이 들어 있다 |
| `.mcp.json`, `mcp/ops_server.py` | 5장(MCP) | 6장의 실습에는 쓰지 않는다. 저장소 상태를 5장 뒤와 맞추기 위한 것으로, 5장 키트의 `설정/mcp.json`과 `교수/ops_server_완성.py`(서버 `jobprep-ops`, 도구 `error_summary`, `status_counts`, `slow_requests`, `read_log`)의 사본이다. `.mcp.json`은 서버를 `python`으로 띄우므로 Claude Code를 가상 환경을 켠 터미널에서 시작해야 한다(Windows에서 `.venv/bin/python` 경로는 없다). 쓰려면 5장 0-3절대로 `requirements.txt`에 `mcp==2.3.0`을 더해 설치한다. 설치하지 않은 채 Claude Code를 열면 `jobprep-ops` 연결 실패가 보일 수 있으나 6장 실습에는 지장이 없다 |

## 복사

저장소 폴더(`~/agent-lab/jobprep`)에서 가상 환경을 켠 터미널로 실행한다(Windows Git Bash `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`). `cp -n`은 이미 있는 파일을 덮어쓰지 않는다.

```bash
B=~/kits/Agent_06장/기준산출물
mkdir -p .claude mcp tools
cp -n $B/tests/.baseline.json tests/
cp -n $B/tools/test_guard.py tools/
cp -n $B/CLAUDE.md .
cp -n $B/.claude/settings.json .claude/
cp -n $B/.mcp.json .
cp -n $B/mcp/ops_server.py mcp/
git status --short
python tools/test_guard.py check
```

동결 검사가 `TEST_CHANGED`를 내면 목록을 읽는다. 4장·5장에서 더한 테스트(`추가`)이거나, 이 기록을 복사한 학습자의 2장 테스트가 기록과 달라서 생긴 것(`수정`, `삭제`)이면, 사람이 확인한 뒤 `python tools/test_guard.py freeze --update`로 자기 저장소를 다시 동결한다. 동결 검사가 통과하지 않은 채로 두면 7절에서 등록하는 테스트 훅이 편집마다 실패를 알린다.
