#!/usr/bin/env bash
# ops/multi/merge.sh: 판정을 통과한 작업 브랜치를 정한 순서대로 통합 브랜치에 병합한다.
# 사람이 실행한다. 이 스크립트를 실행하는 일이 곧 사람의 병합 승인이다.
#
# 사용법 (저장소 맨 위에서, 통합 브랜치 feat/issue-07에 있는 상태로)
#   bash ops/multi/merge.sh ISSUE-07 T1 T2      # 적은 순서가 병합 순서이다
#
# 작업마다 다음을 한다.
#   1. 판정 파일이 「통과」이고, 판정한 커밋이 지금 작업 브랜치의 끝 커밋과 같은지 본다
#      (판정 뒤에 커밋이 더해졌으면 다시 판정해야 한다)
#   2. git merge --no-ff --no-commit 으로 병합을 준비한다
#   3. 충돌이 나면 git merge --abort 로 되돌리고, 충돌한 파일을 알리고 멈춘다 (종료 코드 3)
#   4. 충돌이 없으면 병합된 상태에서 JUDGE_CMD를 돌린다. 실패하면 되돌리고 멈춘다 (종료 코드 4)
#   5. 통과하면 병합 커밋을 만든다
# 앞 작업이 병합된 뒤 멈추면, 병합된 것은 그대로 두고 남은 작업만 알린다.

source "$(dirname "$0")/lib.sh"

[ $# -ge 2 ] || die "사용법: bash ops/multi/merge.sh <이슈> <작업> [작업...]"
ISSUE="$1"; shift
BASE="$(integration_branch "$ISSUE")"
LOGS="$(log_dir "$ISSUE")"

CURRENT="$(git branch --show-current)"
[ "$CURRENT" = "$BASE" ] || die "지금 브랜치는 $CURRENT이다. git switch $BASE 뒤에 실행한다"
require_clean_main

# 병합 전에 모든 판정을 먼저 확인한다. 하나라도 어긋나면 아무것도 병합하지 않는다.
for TASK in "$@"; do
  BR="$(task_branch "$ISSUE" "$TASK")"
  V="$LOGS/판정_$TASK.md"
  [ -f "$V" ] || die "$TASK의 판정 파일 $V가 없다. judge.sh를 먼저 실행한다"
  grep -q '^- 판정: 통과' "$V" || die "$TASK의 판정이 통과가 아니다($V)"
  JUDGED="$(grep -o '판정한 커밋: `[0-9a-f]*`' "$V" | grep -o '[0-9a-f]\{40\}')"
  TIP="$(git rev-parse "$BR")"
  [ "$JUDGED" = "$TIP" ] || die "$TASK: 판정한 커밋(${JUDGED:0:7})과 지금 브랜치 끝(${TIP:0:7})이 다르다. 다시 판정한다"
done

DONE=()
for TASK in "$@"; do
  BR="$(task_branch "$ISSUE" "$TASK")"
  echo "병합  $TASK  ($BR → $BASE)"
  if ! git merge --no-ff --no-commit "$BR" >/dev/null 2>&1; then
    CONFLICTS="$(git -c core.quotepath=false diff --name-only --diff-filter=U | tr '\n' ' ')"
    git merge --abort
    echo "충돌  $TASK: $CONFLICTS" >&2
    echo "      병합을 되돌렸다. 병합된 작업: ${DONE[*]:-없음}. 남은 작업: $*" >&2
    echo "      처리: 해당 작업 공간에서 git merge $BASE 로 충돌을 풀고 커밋한 뒤 judge.sh부터 다시 한다" >&2
    log_event "$ISSUE" "human" "merge_conflict" "$TASK" "files=$CONFLICTS"
    exit 3
  fi
  IGNORES="$(ignore_args "$ISSUE" "$TASK")"   # 아직 병합하지 않은 작업의 인수 테스트는 뺀다
  TEST_CODE=0
  TEST_OUT="$($JUDGE_CMD $IGNORES 2>&1)" || TEST_CODE=$?
  TEST_OUT="${TEST_OUT//$'\r'/}"
  if [ "$TEST_CODE" -ne 0 ]; then
    git merge --abort
    echo "실패  $TASK: 병합한 상태에서 테스트가 실패하여 되돌렸다" >&2
    printf '%s\n' "$TEST_OUT" | tail -5 >&2
    log_event "$ISSUE" "human" "merge_test_failed" "$TASK" "$(printf '%s\n' "$TEST_OUT" | tail -1)"
    exit 4
  fi
  git commit --quiet -m "chore: $ISSUE $TASK 병합 ($BR)"
  DONE+=("$TASK")
  echo "      $(printf '%s\n' "$TEST_OUT" | grep -v '^\s*$' | tail -1)"
  log_event "$ISSUE" "human" "merged" "$TASK" "commit=$(git rev-parse --short HEAD)"
  shift
done
echo "완료  병합한 작업: ${DONE[*]}. 통합 브랜치 $BASE의 끝: $(git log --oneline -1)"
