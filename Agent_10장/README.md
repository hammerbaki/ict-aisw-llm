# Agent_10장 키트: 멀티 에이전트 운영 시스템의 설계

「AI에이전트 기획 및 개발」 10장(학사 12주차)의 실습 키트이다. 이슈 하나(`ISSUE-07` 관심 공고 내보내기 기능과 그 API)를 계획서와 작업 카드로 나누고, 내 PC의 Orca에서 작업 공간(git worktree) 둘을 만들어 자기 계정의 Claude Code 세션 둘이 나란히 구현하게 한 뒤, 판정 스크립트로 판정하고 사람이 정한 순서로 병합한다. 두 작업이 공유 파일(`docs/운영/변경기록.md`)의 같은 자리에 한 줄씩 더하므로 뒤의 병합에서 충돌이 하나 나고, 그 충돌을 뒤 작업의 작업 공간에서 풀어 다시 판정한 뒤 병합한다.

## 들어 있는 것

| 경로 | 내용 | 저장소로 옮기는가 |
|---|---|---|
| `jobprep/.claude/agents/` | 역할 에이전트 정의 `planner.md`, `implementer.md`, `tester.md` | 예 (`cp -rn`) |
| `jobprep/docs/운영/변경기록.md` | 운영 변경 기록. 핵심 실습에서 두 작업이 함께 고치는 공유 파일 | 예 |
| `jobprep/ops/multi/` | 판정·병합·정리 스크립트(`judge.sh`, `merge.sh`, `status.sh`, `cleanup.sh`), 스크립트 조정자(`prepare.sh`, `dispatch.sh`, `run_issue.sh`), 공통 함수 `lib.sh`, 규칙 검토기 `rule_review.py`, 정의 검사기 `check_agents.py`, 테스트 `tests/` | 예 |
| `jobprep/ops/multi/이슈/ISSUE-07.md` | 실습 이슈 카드 | 예 |
| `jobprep/ops/multi/fake/` | 가짜 에이전트(기획, 테스트, 구현)와 정답 변경 `answers/` | 예 |
| `jobprep/ops/multi/견본/ISSUE-07/` | 가짜 기획 에이전트가 쓰는 계획서와 작업 카드의 견본 | 예 |
| `양식/` | 계획서, 작업 카드, 결과 보고, 멀티 에이전트 설계서의 양식 | 복사해 채운다 |
| `기준산출물/` | 앞 장 산출물이 없는 학습자용 견본: 1장 `docs/운영/역할정의.md`, 7장 조립본의 `.claude/agents/reviewer.md`(검토 규칙 RV1~RV8), 8장 `ops/loop/` | 없는 것만 (`cp -rn`) |
| `시연기록/` | 교수 시연(스크립트 조정자로 돌린 실제 Claude Code 실행)의 기록을 교수가 올리는 자리 | 아니오. 읽기만 한다 |

`교수/`는 학생용 배포에 넣지 않는다.

## 쓰는 순서

1. 0절: 키트 저장소를 `git -C ~/kits-repo pull`로 받고 `cp -rn ~/kits-repo/Agent_10장 ~/kits/`로 복사한다(부록 A-7). 기준산출물과 `jobprep/`을 저장소에 `cp -rn`으로 옮긴다. 7장의 하네스(`CLAUDE.md`, `.claude/settings.json`)가 없으면 8장 키트의 `기준산출물/jobprep/`을 먼저 옮긴다. `.gitignore`에 `.claude/worktrees/`를 더한다.
2. 4절: `python ops/multi/check_agents.py`로 정의 파일을 검사하고, 검토자(`reviewer.md`)의 끝에 판정 형식 절을 더한다.
3. 9절의 핵심 실습: `feat/issue-07`에서 계획 승인 → 인수 테스트(Red) → Orca의 작업 공간 둘 → 두 Claude Code 세션의 구현 → `judge.sh`(작업 공간은 작업 브랜치 이름으로 찾는다) → `merge.sh`(충돌을 풀고 다시 판정) → 명세서 갱신 → 작업 공간 정리 → `main` 반영. 설계서 9절에 Orca 작업 공간의 `git worktree list` 출력과 화면 캡처(`docs/운영/인계/ISSUE-07/orca.png`)를 남긴다.
4. `양식/멀티에이전트설계_양식.md`를 `docs/운영/멀티에이전트설계.md`로 복사해 채운다.

모든 명령은 가상 환경을 켠 Git Bash(Windows) 또는 터미널(macOS)에서, 저장소 맨 위(`~/agent-lab/jobprep`)에서 실행한다. 파이썬은 `python`으로 부른다(Windows의 Git Bash에는 `python3`이 없다).

## 실행 상한

실제 모델은 Orca 작업 공간 둘의 Claude Code 대화형 세션(시도 상한 2)에서만 부른다. 스크립트 조정자(`run_issue.sh`에 `claude_impl.sh`)로 실제 모델을 무인으로 되풀이하는 실행과 Orca의 오케스트레이션은 교수 시연이며, 그 기록은 `시연기록/`으로 읽는다. 프로덕트의 LLM 호출은 모의 모드(`LLM_FAKE=1`)이다.

## 확인한 환경

Windows 11의 Git Bash(bash 5.3, git 2.55), Python 3.13, pytest 9.2에서 실행하였다(2026-11-17). 스크립트는 bash 4 이상이 필요하다(`declare -A`, `mapfile`). macOS의 기본 bash(3.2)에서는 돌지 않으므로 Homebrew의 bash를 쓴다. 스크립트 테스트(`python -m pytest -q ops/multi/tests`)는 Windows에서 프로세스를 많이 띄우므로 20분 넘게 걸린다. 수업에서는 돌리지 않고, 교수가 수업 전에 한 번 돌린다.
