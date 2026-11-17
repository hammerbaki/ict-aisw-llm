#!/usr/bin/env bash
# ops/multi/run_issue.sh: 스크립트가 조정자가 되어 이슈 하나를 「준비 → 병렬 구현 → 판정 → 재작업」까지 돌린다.
# 병합은 하지 않는다. 병합은 사람이 판정을 읽고 merge.sh로 한다(사람의 승인 지점).
#
# 사용법 (저장소 맨 위에서, 통합 브랜치에 계획서·카드·인수 테스트를 커밋한 뒤)
#   AGENT_CMD="python ops/multi/fake/impl_agent.py" bash ops/multi/run_issue.sh ISSUE-07 T1 T2
#
# 환경 변수
#   AGENT_CMD   구현 에이전트 명령 (dispatch.sh와 같다)
#   MULTI_MAX   작업마다의 시도 상한 (3). 상한까지 통과하지 못한 작업은 사람에게 넘긴다
#   REVIEW_CMD  검토 명령 (judge.sh와 같다)
# 종료 코드: 모든 작업이 통과 0, 상한에 닿은 작업이 있음 1, 시작 조건 실패 2.

source "$(dirname "$0")/lib.sh"

[ $# -ge 2 ] || die "사용법: AGENT_CMD=... bash ops/multi/run_issue.sh <이슈> <작업> [작업...]"
ISSUE="$1"; shift
MAX="${MULTI_MAX:-3}"
HERE="ops/multi"

bash "$HERE/prepare.sh" "$ISSUE" "$@" || exit 2
log_event "$ISSUE" "coordinator" "run_started" "" "tasks=$* max=$MAX"

PENDING=("$@")
PASSED=()
ATTEMPT=1
while [ "${#PENDING[@]}" -gt 0 ] && [ "$ATTEMPT" -le "$MAX" ]; do
  echo "== 시도 $ATTEMPT/$MAX: ${PENDING[*]}"
  MULTI_ATTEMPT="$ATTEMPT" MULTI_MAX="$MAX" bash "$HERE/dispatch.sh" "$ISSUE" "${PENDING[@]}"
  NEXT=()
  for TASK in "${PENDING[@]}"; do
    if bash "$HERE/judge.sh" "$ISSUE" "$TASK" > /dev/null; then
      echo "통과  $TASK"
      PASSED+=("$TASK")
    else
      echo "거부  $TASK  (사유: $(log_dir "$ISSUE")/판정_$TASK.md)"
      NEXT+=("$TASK")
    fi
  done
  PENDING=("${NEXT[@]}")
  ATTEMPT=$((ATTEMPT + 1))
done

if [ "${#PENDING[@]}" -eq 0 ]; then
  echo "== 모든 작업이 판정을 통과하였다: ${PASSED[*]}"
  echo "   다음: 판정 파일과 결과 보고를 읽고, 병합 순서를 정해 bash $HERE/merge.sh $ISSUE <작업...>"
  log_event "$ISSUE" "coordinator" "ready_to_merge" "" "passed=${PASSED[*]}"
  exit 0
fi
echo "== 상한($MAX회)에 닿아 사람에게 넘긴다: ${PENDING[*]}  (통과: ${PASSED[*]:-없음})"
log_event "$ISSUE" "coordinator" "handed_to_human" "" "pending=${PENDING[*]}"
exit 1
