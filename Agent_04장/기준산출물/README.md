# 기준산출물: 3장 결과의 규칙 파일

3장(팀 규칙의 공유)을 마치지 못한 학습자가 4장을 시작할 수 있게 넣은 견본이다. 3장을 마친 학습자는 이 폴더를 쓰지 않는다. 내용은 3장 키트의 교수 완성본(`Agent_03장/교수/완성본/`)에서 이 장이 기대는 규칙 파일 넷을 제자리 이름으로 옮긴 것이다(장 사이 정합 기준 3절).

| 파일 | 저장소에서의 위치 | 3장 완성본의 이름 | 내용 |
|---|---|---|---|
| `CLAUDE.md` | `jobprep/CLAUDE.md` | `팀_CLAUDE.md` | 팀 규칙(실행 명령, 작업 규칙, 금지와 그 이유) |
| `.claude/rules/api.md` | `jobprep/.claude/rules/api.md` | `rules_api.md` | `api/**/*.py`를 다룰 때만 읽히는 경로별 규칙 |
| `.claude/rules/tests.md` | `jobprep/.claude/rules/tests.md` | `rules_tests.md` | `tests/**/*.py`를 다룰 때만 읽히는 경로별 규칙 |
| `.claude/settings.json` | `jobprep/.claude/settings.json` | `settings.json` | 공유 권한 규칙(허용, 확인, 거부) |

받는 명령(이미 같은 파일이 있으면 덮어쓰지 않는다):

```bash
cd ~/agent-lab/jobprep
cp -n ~/kits/Agent_04장/기준산출물/CLAUDE.md .
mkdir -p .claude/rules
cp -n ~/kits/Agent_04장/기준산출물/.claude/settings.json .claude/
cp -n ~/kits/Agent_04장/기준산출물/.claude/rules/*.md .claude/rules/
git add CLAUDE.md .claude/settings.json .claude/rules
git commit -m "chore(claude): 3장 기준산출물(팀 CLAUDE.md, 경로별 규칙, 공유 설정) 반영"
```

3장의 나머지 산출물(저장소 규약 문서, PR 템플릿, CODEOWNERS, 규칙 비교, 검사 도구 `ops/rules/`)은 4장 실습에 필요하지 않으므로 넣지 않았다. 그래서 `CLAUDE.md`가 가리키는 `docs/운영/저장소규약.md`, `ops/rules/`, `tools/test_guard.py`가 저장소에 없을 수 있다. 4장의 명령은 이 파일들에 기대지 않는다.
