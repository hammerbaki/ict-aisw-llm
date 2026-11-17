# 기준 산출물 (2~6장을 마치지 못한 학습자용)

7장은 1~6장의 부품이 저장소에 있다고 보고 조립한다. 부품이 없는 학습자는 이 폴더의 파일을 저장소에 복사해 출발점을 맞춘다. 앞 장을 마친 학습자는 자기 파일을 쓴다(`cp -n`은 이미 있는 파일을 덮어쓰지 않는다). 모두 견본이며 각 장의 완성본이 아니다.

| 파일 | 원래 만드는 장 | 출처 |
|---|---|---|
| `tests/.baseline.json` | 2장(테스트 동결) | 6장 키트의 기준 산출물과 같다. 2장 정답 저장소를 2장의 검사기로 동결한 새 형식 기록(`version`, `frozen_at`, `files`, 파일 11개) |
| `tools/test_guard.py` | 2장(동결 검사기) | 2장 키트의 `도구/test_guard.py`와 같다 |
| `CLAUDE.md`, `.claude/rules/api.md`, `.claude/rules/web.md`, `docs/운영/저장소규약.md` | 3장(팀 규칙) | 4장·6장 키트의 견본을 합치고 규칙 7(기록)과 8(명세)을 더하였다 |
| `.claude/settings.json` | 3장(권한), 6장(훅 등록) | 4장 키트의 권한 견본 + 6장 키트의 `훅설정.json` |
| `plugins/jobprep-ops/`, `.claude-plugin/marketplace.json` | 4장(스킬과 플러그인) | 4장 키트의 `예비/`와 `재료/incident-report/`를 4장 본문의 배치대로 놓았다 |
| `.mcp.json`, `mcp/ops_server.py` | 5장(MCP) | 5장 키트의 `설정/mcp.json`과 `교수/ops_server_완성.py`(서버 `jobprep-ops`, 도구 `error_summary`, `status_counts`, `slow_requests`, `read_log`). `mcp==2.3.0`이 필요하다 |
| `.claude/hooks/` | 6장(훅) | 6장 키트의 `hooks/`(편집 뒤 테스트 훅과 점검 스크립트에 동결 검사 포함). `protected.txt`에 6장 4-5절의 `data/jobs.json` 두 줄을 더하였다 |
| `.claude/agents/reviewer.md` | 6장(검토 서브에이전트) | 6장 키트의 완성본 `교수/reviewer.md`(검토 규칙 RV1~RV6) |

6장의 부품(훅, 검토자)과 5장의 MCP 서버, 동결 기록은 정합 작업(2026-11-14)에서 6장 키트의 최신 파일로 다시 복사하였다. 복사 명령은 7장 강의안 0-3절에 있다. 복사한 뒤 `tools/test_guard.py check`가 `TEST_CHANGED`이면 6장 0-3절처럼 사람이 확인하고 `freeze --update`로 다시 동결한다.
