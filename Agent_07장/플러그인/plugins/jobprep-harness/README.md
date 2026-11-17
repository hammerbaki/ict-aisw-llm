# jobprep-harness 플러그인

jobprep 계열 저장소에서 함께 쓰는 하네스 부품을 묶은 플러그인이다(7장 8절). 장애 보고서 스킬은 4장의 `jobprep-ops` 플러그인에 있으므로 여기서는 의존(`dependencies`)으로만 건다.

| 부품 | 파일 | 막는 실패 |
|---|---|---|
| 보호 파일 훅(PreToolUse) | `scripts/protect.sh`, `scripts/protected.txt` | `.env`, 동결 기록, 동결된 테스트, 공고 데이터의 편집 |
| 편집 뒤 테스트 훅(PostToolUse) | `scripts/run_tests.sh` | 문법 오류와 관련 테스트 실패를 모른 채 다음 단계로 가는 것 |
| 완료 전 테스트 관문(Stop) | `scripts/stop_gate.sh` | 전체 테스트가 실패하는데 끝났다고 보고하는 것(한 번 되돌린 뒤 사람에게) |
| 검토 서브에이전트 | `agents/reviewer.md` | 구현한 쪽의 자기 검토가 놓치는 규칙 위반(RV1~RV8) |

## 플러그인에 넣지 않은 것과 그 까닭

- `CLAUDE.md`: 플러그인 안의 `CLAUDE.md`는 컨텍스트에 실리지 않는다. 저장소마다 다른 명령과 규칙은 각 저장소의 `CLAUDE.md`에 둔다.
- 권한 규칙(`permissions`): 플러그인 구성 요소가 아니다. 저장소의 `.claude/settings.json`에 둔다.
- MCP 서버 `jobprep-ops`: 서버 코드(`mcp/ops_server.py`)가 jobprep 저장소에 있고 기록 형식도 jobprep의 것이다. 저장소의 `.mcp.json`에 둔다.

## 필요 조건

- 훅 스크립트는 bash와 파이썬(JSON 읽기)을 쓴다. Windows에서는 Git for Windows의 bash로 돈다.
- 훅은 환경 변수 `JOBPREP_PYTHON`이 있으면 그것을, 없으면 저장소의 `.venv/Scripts/python.exe`(Windows), `.venv/bin/python`(macOS, 리눅스), PATH의 `python` 순서로 파이썬을 고른다(부록 A-9-2). 테스트 훅은 그 파이썬으로 pytest를 돌린다.
- 보호 목록은 저장소의 `.claude/hooks/protected.txt`가 있으면 그것을, 없으면 플러그인의 `scripts/protected.txt`를 쓴다.
- 같은 훅이 저장소의 `.claude/settings.json`에도 있으면 두 번 돈다. 플러그인을 켠 저장소에서는 설정 파일의 같은 훅을 지운다.

## 설치

마켓플레이스가 든 저장소가 GitHub에 있으면 Claude Code 안에서 다음 한 줄로 설치한다(`<계정>/jobprep`은 자기 저장소로 바꾼다).

```text
/plugin install jobprep-harness --marketplace <계정>/jobprep
```

저장소를 내려받은 컴퓨터에서는 셸에서 `claude plugin marketplace add ./`와 `claude plugin install jobprep-harness@jobprep-team`으로도 설치한다.
