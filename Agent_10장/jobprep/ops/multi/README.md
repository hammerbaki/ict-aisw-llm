# ops/multi: 멀티 에이전트 조정 스크립트

이슈 하나를 「계획 → 인수 테스트 → 병렬 구현 → 판정 → 병합 → 정리」로 돌리는 스크립트이다. 「AI에이전트 기획 및 개발」 10장에서 쓴다. 모든 스크립트는 저장소 맨 위에서, 가상 환경을 켠 Git Bash(Windows) 또는 터미널(macOS)에서 실행한다.

10장의 핵심 실습은 작업 공간을 Orca로 만들고 두 Claude Code 세션을 사람이 조정한다. 그때 이 폴더에서 쓰는 것은 `judge.sh`, `merge.sh`, `status.sh`, `check_agents.py`이다. `prepare.sh`, `dispatch.sh`, `run_issue.sh`는 같은 흐름을 스크립트가 조정하는 길(교수 시연, Orca를 쓸 수 없을 때의 대비)이다.

## 이름 규칙

| 대상 | 이름 (ISSUE-07, 작업 T1) |
|---|---|
| 통합 브랜치 | `feat/issue-07` (계획서와 인수 테스트가 먼저 올라간다) |
| 작업 브랜치 | `agent/issue-07-t1` |
| 작업 공간 | `.claude/worktrees/issue-07-t1` (`.gitignore`에 있다). Orca처럼 다른 도구가 만든 작업 공간은 작업 브랜치 이름(`agent/issue-07-t1`)으로 `git worktree list --porcelain`에서 찾는다(폴더 이름과 위치에 상관없다) |
| 인계 문서 | `docs/운영/인계/ISSUE-07/` (계획서, `T1_카드.md`, `T1_보고.md`) |
| 실행 기록 | `ops/multi/logs/ISSUE-07/` (`events.jsonl`, `판정_T1.md`, 에이전트 출력) |

## 스크립트

| 스크립트 | 하는 일 | 누가 실행하는가 |
|---|---|---|
| `prepare.sh 이슈 작업...` | 승인과 소유 파일 겹침을 확인하고 작업마다 worktree와 브랜치를 만든다 | 조정자 |
| `dispatch.sh 이슈 작업...` | `AGENT_CMD`를 작업 공간마다 병렬로 실행한다 | 조정자 |
| `judge.sh 이슈 작업` | 커밋, 범위, 동결, 보고, 테스트, 검토를 판정한다 | 조정자(테스트·검토 역할의 자리) |
| `run_issue.sh 이슈 작업...` | 위 셋을 시도 상한까지 되풀이한다(스크립트 조정자) | 조정자 |
| `merge.sh 이슈 작업...` | 판정을 통과한 브랜치를 적은 순서대로 통합 브랜치에 병합한다 | **사람** |
| `status.sh 이슈` | 작업 공간, 브랜치, 판정, 병합 상태를 표로 보인다 | 누구나 |
| `cleanup.sh 이슈 작업...` | 병합된 작업의 worktree와 브랜치를 지운다 | 조정자 |
| `rule_review.py` | 기계로 잴 수 있는 팀 규칙(W1~W4)만 보는 규칙 검토기. `judge.sh`의 기본 검토 명령 | `judge.sh` |
| `check_agents.py` | `.claude/agents/`의 정의 파일을 검사한다(알 수 없는 필드, 모델 이름, 빈 본문) | 누구나 |
| `claude_impl.sh` | 실제 Claude Code로 구현 에이전트를 실행하는 감싸개(`AGENT_CMD`로 쓴다) | `dispatch.sh` |
| `claude_review.sh` | 실제 Claude Code로 검토 에이전트를 실행하는 감싸개(`REVIEW_CMD`로 쓴다) | `judge.sh` |

## 환경 변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `AGENT_CMD` | 없음(꼭 정한다) | 구현 에이전트 명령. 작업 공간 안에서 실행되고 마지막 인자로 지시문을 받는다 |
| `REVIEW_CMD` | `python ops/multi/rule_review.py` | 검토 명령. 표준 입력으로 차이를 받고 출력에 「판정: 통과」가 있어야 한다 |
| `JUDGE_CMD` | `.venv의 python -m pytest -q` | 판정 명령 |
| `MULTI_MAX` | `3` | 작업마다의 시도 상한 |
| `MULTI_PY` | 저장소의 가상 환경 파이썬(`.venv/Scripts/python.exe`, 없으면 `.venv/bin/python`, 둘 다 없으면 `python`) | 판정과 검토에 쓰는 파이썬 |
| `MULTI_WT_BASE` | 없음 | 주면 그 폴더 아래의 `issue-07-t1` 꼴 이름만 본다(옛 방식). 주지 않으면 `.claude/worktrees/issue-07-t1`, 없으면 작업 브랜치를 꺼낸 worktree를 찾는다 |

## 작업 카드에서 스크립트가 읽는 줄

| 줄 | 뜻 | 쓰는 곳 |
|---|---|---|
| `- 소유 파일:` | 이 작업만 고치는 파일. 두 카드에 같은 경로가 있으면 `prepare.sh`가 거부한다 | `prepare.sh`, `judge.sh`의 범위 |
| `- 공유 파일:` | 여러 작업이 함께 고치는 파일(끝에 한 줄을 더하는 기록 등). 겹쳐도 거부하지 않고 「공유」 줄로 알린다. 같은 자리를 고치면 병합 때 충돌한다 | `prepare.sh`, `judge.sh`의 범위 |
| `- 인수 테스트:` | 이 작업의 판정에 쓰는 테스트. 아직 병합되지 않은 다른 작업의 판정에서는 뺀다 | `judge.sh`, `merge.sh` |

경로는 역따옴표로 감싸고 쉼표로 나눈다. 카드는 작업 공간이 아니라 통합 브랜치의 커밋에서 읽는다.

## 종료 코드

`0` 성공, `1` 거부 또는 상한 도달, `2` 시작 조건 실패, `3` 병합 충돌(되돌림), `4` 병합 뒤 테스트 실패(되돌림).

## 가짜 에이전트 (`fake/`)

모델을 부르지 않고 같은 흐름을 돌리기 위한 대역이다. `plan_agent.py`(계획서와 카드), `test_agent.py`(인수 테스트), `impl_agent.py`(정답 변경, 시나리오 `ok`, `fail_once`, `scope`, `crash`). 실제 Claude Code로 바꾸어 넣는 법은 10장 8절에 있다.

## 테스트

```bash
python -m pytest -q ops/multi/tests
```

연습 저장소를 임시 폴더에 만들어 스크립트를 실제로 실행한다. bash와 git이 필요하다.
