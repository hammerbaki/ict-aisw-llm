#!/usr/bin/env bash
# ops/multi/cleanup.sh: 병합이 끝난 작업의 작업 공간(worktree)과 작업 브랜치를 지운다.
#
# 사용법 (저장소 맨 위에서)
#   bash ops/multi/cleanup.sh ISSUE-07 T1 T2
#
# 지우지 않는 경우 (그 작업만 건너뛰고 까닭을 알린다)
#   - 작업 공간에 커밋하지 않은 변경이나 추적하지 않는 파일이 있다 (git worktree remove가 거부한다)
#   - 작업 브랜치가 통합 브랜치에 병합되지 않았다 (git branch -d가 거부한다)
# 강제로 지우는 옵션(--force, -D)은 두지 않았다. 일을 잃을 수 있는 삭제는 사람이 직접 판단해 명령으로 한다.

source "$(dirname "$0")/lib.sh"

[ $# -ge 2 ] || die "사용법: bash ops/multi/cleanup.sh <이슈> <작업> [작업...]"
ISSUE="$1"; shift
BASE="$(integration_branch "$ISSUE")"
STATUS=0
for TASK in "$@"; do
  BR="$(task_branch "$ISSUE" "$TASK")"
  DIR="$(task_dir "$ISSUE" "$TASK")"
  if ! is_merged "$ISSUE" "$TASK"; then
    echo "건너뜀  $TASK: $BR가 merge.sh로 $BASE에 병합되지 않았다. 버릴 작업이면 사람이 git worktree remove와 git branch -D로 지운다" >&2
    STATUS=1; continue
  fi
  if [ -d "$DIR" ]; then
    if ! git worktree remove "$DIR"; then
      echo "건너뜀  $TASK: 작업 공간 $DIR에 남은 변경이 있다. 확인한 뒤 직접 지운다" >&2
      STATUS=1; continue
    fi
  fi
  # 통합 브랜치에 병합되었으므로 -d가 받아들인다. 지금 브랜치가 통합 브랜치가 아니면 -d가 거부할 수 있다.
  if git branch -d "$BR" >/dev/null; then
    echo "지움    $TASK: $DIR, $BR"
    log_event "$ISSUE" "coordinator" "cleaned" "$TASK" "$DIR $BR"
  else
    STATUS=1
  fi
done
git worktree prune
exit "$STATUS"
