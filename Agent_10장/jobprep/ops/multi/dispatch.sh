#!/usr/bin/env bash
# ops/multi/dispatch.sh: 작업 카드를 구현 에이전트에게 나누어 주고 병렬로 실행한다.
#
# 사용법 (저장소 맨 위에서, prepare.sh 다음에)
#   AGENT_CMD="<에이전트 명령>" bash ops/multi/dispatch.sh ISSUE-07 T1 T2
#
# AGENT_CMD의 예
#   가짜 에이전트(수업의 기본):  AGENT_CMD="python ops/multi/fake/impl_agent.py"
#   Claude Code(헤드리스):       AGENT_CMD="claude -p --agent implementer --permission-mode acceptEdits --max-budget-usd 0.50"
# 에이전트 명령은 작업 공간(worktree) 안에서 실행되고, 마지막 인자로 지시문 하나를 받는다.
#
# 환경 변수
#   MULTI_ATTEMPT   이번이 몇 번째 시도인가 (1)
#   MULTI_MAX       시도 상한 (3). 지시문에 「시도 n/상한」으로 적는다
# 결과: 작업마다 ops/multi/logs/<이슈>/<작업>_시도<n>.out 에 에이전트의 출력을 남긴다.
# 종료 코드: 모든 에이전트가 0으로 끝나면 0, 하나라도 아니면 1, 시작 조건 실패는 2.

source "$(dirname "$0")/lib.sh"

[ $# -ge 2 ] || die "사용법: AGENT_CMD=... bash ops/multi/dispatch.sh <이슈> <작업> [작업...]"
[ -n "${AGENT_CMD:-}" ] || die "AGENT_CMD가 비었다. 가짜 에이전트: AGENT_CMD=\"python ops/multi/fake/impl_agent.py\""
ISSUE="$1"; shift
ATTEMPT="${MULTI_ATTEMPT:-1}"
MAX="${MULTI_MAX:-3}"
read -r -a CMD <<< "$AGENT_CMD"
LOGS="$(log_dir "$ISSUE")"
mkdir -p "$LOGS"

declare -A PIDS=() STARTED=()
for TASK in "$@"; do
  DIR="$(task_dir "$ISSUE" "$TASK")"
  [ -d "$DIR" ] || die "$DIR가 없다. prepare.sh를 먼저 실행한다"
  CARD="$(card_path "$ISSUE" "$TASK")"
  REPORT="$(report_path "$ISSUE" "$TASK")"
  PROMPT="이 작업 공간은 이슈 $ISSUE의 작업 $TASK 전용이다. 작업 카드 $CARD를 읽고 그대로 수행하라. "
  PROMPT+="카드의 소유 파일과 공유 파일 밖의 파일은 고치지 않는다. 끝나면 결과 보고를 $REPORT에 쓰고, "
  PROMPT+="그 파일들만 git add 하여 커밋하라. 푸시와 병합은 하지 않는다. 시도 $ATTEMPT/$MAX."
  VERDICT="$MAIN_ROOT/$LOGS/판정_$TASK.md"
  if [ "$ATTEMPT" -gt 1 ] && [ -f "$VERDICT" ]; then
    # 판정 파일은 기본 작업 공간에 있으므로, 작업 공간 밖을 읽지 않아도 되게 거부 사유를 지시문에 붙인다.
    PROMPT+=$'\n\n직전 판정의 거부 사유를 먼저 고친다.\n'"$(sed -n '/^| 항목/,/^$/p' "$VERDICT")"
  fi
  OUT="$MAIN_ROOT/$LOGS/${TASK}_시도${ATTEMPT}.out"
  ( cd "$DIR" && "${CMD[@]}" "$PROMPT" ) > "$OUT" 2>&1 &
  PIDS[$TASK]=$!
  STARTED[$TASK]=$SECONDS
  echo "시작  $TASK  (pid ${PIDS[$TASK]}, 작업 공간 $DIR)"
  log_event "$ISSUE" "implementer:$TASK" "dispatched" "$TASK" "attempt=$ATTEMPT cmd=${CMD[0]}"
done

STATUS=0
for TASK in "$@"; do
  if wait "${PIDS[$TASK]}"; then CODE=0; else CODE=$?; fi
  SEC=$(( SECONDS - STARTED[$TASK] ))
  echo "끝남  $TASK  종료 코드 $CODE, ${SEC}초, 출력 $LOGS/${TASK}_시도${ATTEMPT}.out"
  log_event "$ISSUE" "implementer:$TASK" "finished" "$TASK" "attempt=$ATTEMPT exit=$CODE seconds=$SEC"
  [ "$CODE" -eq 0 ] || STATUS=1
done
exit "$STATUS"
