# 기준산출물: 8장과 10장의 실행 기록 견본

12장은 8장(루프 엔지니어링)과 10장(멀티 에이전트)의 실행 기록을 읽어 에이전트의 작업 성공률, 사람 개입, 비용을 보고한다. 앞 장을 마치지 못해 기록이 없는 학습자는 이 견본을 저장소에 복사해 쓴다. 기록은 2027-11의 가상 실행이며, 비용은 지어낸 값이다.

## ops/loop/logs/*.jsonl (8장 루프 실행 기록)

한 줄이 사건 하나인 JSON Lines이다. `event`는 `start`, `judge`, `attempt`, `end` 가운데 하나다.

| 사건 | 주요 칸 |
|---|---|
| `start` | `config`(최대 시도 `max_attempts`, 예산 `budget`, 판정 명령 `judge_cmd`, 보호 경로 `protected`) |
| `judge` | 시작 전 판정: `judge_exit`(pytest의 종료 코드), `failures`(실패한 테스트 수) |
| `attempt` | `attempt`(번호), `subtype`(헤드리스 실행 결과의 종류), `cost_usd`, `turns`, `agent_seconds`, `changed`, `judge_exit`, `decision`(`commit`, `checkpoint`, `restore`, `no_change`), `spent_usd`(누적) |
| `end` | `status`(`green`, `gave_up`, `budget`), `exit_code`, `attempts`, `spent_usd`, 실패하면 `report` |

견본 7건 가운데 `2027-11-06-sort-order`는 커밋한 시도가 `tests/test_jobs.py`를 고쳐 통과한 실행이다(8장 6-8의 `cheat-1`과 같은 모양). 12장의 `ops/telemetry/report.py`는 `start.config.protected`와 커밋된 시도의 `changed`를 대조해 이런 실행을 「의심 성공」으로 따로 센다.

`cost_usd`와 `turns`는 `claude -p --output-format json`이 내는 결과 객체의 `total_cost_usd`와 `num_turns`를 옮긴 것이다(8장 `fix_until_green.py`의 `run_agent()`). 칸 이름과 순서는 8장 키트의 `교수/fix_until_green_정답.py`가 쓰는 기록과 같다(되돌린 시도의 `diff`에는 그 시도의 변경을 남긴 파일 경로가 들어간다).

## ops/multi/logs/<이슈>/ (10장 멀티 에이전트 실행 기록)

10장의 `ops/multi/lib.sh`가 남기는 형식 그대로이다. 이슈 번호(ISSUE-12, ISSUE-15, ISSUE-18)는 10장 실습의 ISSUE-07과 겹치지 않게 골랐다.

| 파일 | 내용 |
|---|---|
| `events.jsonl` | 한 줄이 사건 하나. 칸: `time`, `issue`, `actor`(`coordinator`, `implementer:T1`, `judge`, `human`), `event`, `task`, `detail` |
| `<작업>_시도<n>.out` | 구현 에이전트의 출력. `claude -p --output-format json`의 결과 객체를 본뜬 것으로 `total_cost_usd`, `num_turns`, `session_id`, `result`가 있다 |

| 사건(`event`) | 쓰는 스크립트 | `detail`의 예 |
|---|---|---|
| `worktree_created`, `cleaned` | `prepare.sh`, `cleanup.sh` | `.claude/worktrees/issue-12-t1 agent/issue-12-t1` |
| `run_started`, `ready_to_merge`, `handed_to_human` | `run_issue.sh` | `tasks=T1 T2 max=3`, `passed=T1 T2` |
| `dispatched`, `finished` | `dispatch.sh` | `attempt=2 cmd=bash`, `attempt=1 exit=0 seconds=212` |
| `judged` | `judge.sh` | `verdict=통과 commit=3f1a9c2`, `verdict=거부 commit=e19b6c3` |
| `merged`, `merge_conflict`, `merge_test_failed` | `merge.sh`(사람이 실행) | `commit=a61d0f4`, `files=docs/요구사항명세서.md` |

견본의 줄거리: ISSUE-12는 두 작업이 첫 시도에 통과해 병합되었다. ISSUE-15는 T2의 첫 시도가 규칙 검토(W1, `innerHTML`)에서 거부되어 두 번째 시도에 통과하였다. ISSUE-18은 T1의 병합이 명세서 충돌로 멈추었고(`merge_conflict`), 사람이 작업 공간에서 충돌을 푼 뒤 다시 판정해 병합하였다.

10장의 커밋 꼬리말(`Agent-Role`, `Agent-Task`, `Agent-Attempt`)은 git 기록에 있으므로 견본에 넣지 않았다. `ops/telemetry/report.py`는 저장소의 `git log`에서 꼬리말을 읽고, 견본만 있는 저장소에서는 「꼬리말이 붙은 커밋이 없다」고 보고한다.

10장의 핵심 실습처럼 Orca 작업 공간의 세션에 사람이 지시를 넣은 이슈에는 `dispatched` 사건과 `.out` 파일이 없고 `judged`, `merged`, `merge_conflict`만 남는다. `report.py`는 이런 이슈를 「실행 사건(dispatched)이 없는 이슈」로 따로 적고 시도를 판정 횟수로 센다(2026-11-17 더함).

10장에서 사건 이름을 바꾼 학습자는 `ops/telemetry/report.py`의 `read_multi()`, `issue_summary()`, `multi_section()`에서 이름만 맞춘다.
