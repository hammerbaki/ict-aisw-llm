#!/usr/bin/env bash
# ops/multi/prepare.sh: 작업마다 git worktree와 작업 브랜치를 만든다.
#
# 사용법 (저장소 맨 위에서)
#   bash ops/multi/prepare.sh ISSUE-07 T1 T2
#
# 시작 조건 (하나라도 어기면 아무것도 만들지 않고 종료 코드 2로 멈춘다)
#   1. 기본 작업 공간이 깨끗하다(실행 기록 폴더는 빼고 본다)
#   2. 통합 브랜치 feat/issue-07이 있고, 그 브랜치의 계획서에 사람의 승인 줄이 있다
#   3. 작업마다 작업 카드가 통합 브랜치에 있고, 카드에 「- 소유 파일:」 줄이 있다
#   4. 두 작업의 소유 파일이 겹치지 않는다(병렬 작업의 충돌을 계획 단계에서 막는다)
#      카드의 「- 공유 파일:」은 겹쳐도 거부하지 않고 「공유」 줄로 알린다(병합 때 충돌할 수 있다)
# 결과: .claude/worktrees/issue-07-t1 (브랜치 agent/issue-07-t1) 등. 이미 있으면 그대로 둔다.

source "$(dirname "$0")/lib.sh"

[ $# -ge 2 ] || die "사용법: bash ops/multi/prepare.sh <이슈> <작업> [작업...]"
ISSUE="$1"; shift
BASE="$(integration_branch "$ISSUE")"

require_clean_main
git rev-parse --verify --quiet "$BASE" >/dev/null || die "통합 브랜치 $BASE가 없다. 계획서를 올린 브랜치를 먼저 만든다"
require_approval "$ISSUE"

# 카드 검사와 소유 파일의 겹침 검사
declare -A OWNER=() SHARERS=()
TMP_CARD="$(mktemp)"
trap 'rm -f "$TMP_CARD"' EXIT
for TASK in "$@"; do
  CARD="$(card_path "$ISSUE" "$TASK")"
  git show "$BASE:$CARD" > "$TMP_CARD" 2>/dev/null || die "$BASE에 작업 카드 $CARD가 없다"
  mapfile -t FILES < <(owned_files "$TMP_CARD")
  [ "${#FILES[@]}" -gt 0 ] || die "$CARD에 「- 소유 파일:」 줄이 없거나 경로가 비었다"
  for F in "${FILES[@]}"; do
    if [ -n "${OWNER[$F]:-}" ]; then
      die "$F를 ${OWNER[$F]}와 $TASK가 함께 소유한다. 한 파일의 소유자는 하나여야 한다(계획서를 고친다)"
    fi
    OWNER[$F]="$TASK"
  done
  mapfile -t SFILES < <(shared_files "$TMP_CARD")
  for F in "${SFILES[@]}"; do
    [ -n "$F" ] && SHARERS[$F]="${SHARERS[$F]:-}${SHARERS[$F]:+ }$TASK"
  done
done
# 공유 파일은 거부하지 않는다. 다만 다른 작업의 소유 파일을 공유 파일로 적으면 소유 규칙이 깨지므로 거부한다.
for F in "${!SHARERS[@]}"; do
  if [ -n "${OWNER[$F]:-}" ]; then
    die "$F는 ${OWNER[$F]}의 소유 파일인데 ${SHARERS[$F]}가 공유 파일로 적었다(계획서를 고친다)"
  fi
  echo "공유  $F: ${SHARERS[$F]} (함께 고친다. 같은 자리를 고치면 병합할 때 충돌한다)"
done

mkdir -p "$WT_BASE"
for TASK in "$@"; do
  BR="$(task_branch "$ISSUE" "$TASK")"
  DIR="$(task_dir "$ISSUE" "$TASK")"
  if [ -d "$DIR" ]; then
    echo "있음  $DIR ($BR)"
    continue
  fi
  if git rev-parse --verify --quiet "$BR" >/dev/null; then
    git worktree add --quiet "$DIR" "$BR" || die "$DIR를 만들지 못하였다"
  else
    git worktree add --quiet -b "$BR" "$DIR" "$BASE" || die "$DIR를 만들지 못하였다"
  fi
  # .env는 저장소에 없으므로 작업 공간에 따라오지 않는다. 테스트는 모의 모드로 돌므로 복사하지 않는다.
  echo "만듦  $DIR ($BR, 기준 $BASE $(git rev-parse --short "$BASE"))"
  log_event "$ISSUE" "coordinator" "worktree_created" "$TASK" "$DIR $BR"
done
