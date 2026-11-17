#!/usr/bin/env bash
# ops/multi/status.sh: 이슈 하나의 작업 공간, 브랜치, 판정, 병합 상태를 한눈에 본다.
#
# 사용법 (저장소 맨 위에서)
#   bash ops/multi/status.sh ISSUE-07
#
# 열의 뜻
#   앞섬   통합 브랜치에 없고 작업 브랜치에만 있는 커밋 수
#   뒤짐   작업 브랜치에 없고 통합 브랜치에만 있는 커밋 수(다른 작업이 먼저 병합되면 늘어난다)
#   변경   작업 공간에서 커밋하지 않은 파일 수
#   판정   판정 파일의 결과. 판정 뒤에 커밋이 더해졌으면 「낡음」
#   병합   작업 브랜치의 끝 커밋이 통합 브랜치에 들어갔는가

source "$(dirname "$0")/lib.sh"

[ $# -eq 1 ] || die "사용법: bash ops/multi/status.sh <이슈>"
ISSUE="$1"
BASE="$(integration_branch "$ISSUE")"
SLUG="$(issue_slug "$ISSUE")"
LOGS="$(log_dir "$ISSUE")"
git rev-parse --verify --quiet "$BASE" >/dev/null || die "통합 브랜치 $BASE가 없다"

echo "이슈 $ISSUE   통합 브랜치 $BASE ($(git rev-parse --short "$BASE"))   지금 브랜치 $(git branch --show-current)"
echo "| 작업 | 브랜치 | 앞섬 | 뒤짐 | 변경 | 판정 | 병합 | 작업 공간 |"

mapfile -t BRANCHES < <(git for-each-ref --format='%(refname:short)' "refs/heads/agent/$SLUG-*")
if [ "${#BRANCHES[@]}" -eq 0 ]; then
  echo "(작업 브랜치가 없다)"
fi
for BR in "${BRANCHES[@]}"; do
  TASK="$(echo "${BR##*-}" | tr '[:lower:]' '[:upper:]')"
  DIR="$(task_dir "$ISSUE" "$TASK")"
  read -r BEHIND AHEAD < <(git rev-list --left-right --count "$BASE...$BR")
  if [ -d "$DIR" ]; then
    CHANGES="$(git -C "$DIR" status --porcelain | wc -l | tr -d ' ')"
    WT="$DIR"
  else
    CHANGES="-"; WT="(없음)"
  fi
  V="$LOGS/판정_$TASK.md"
  if [ -f "$V" ]; then
    RESULT="$(sed -n 's/^- 판정: //p' "$V")"
    JUDGED="$(grep -o '[0-9a-f]\{40\}' "$V" | head -1)"
    [ "$JUDGED" = "$(git rev-parse "$BR")" ] || RESULT="낡음"
  else
    RESULT="없음"
  fi
  if is_merged "$ISSUE" "$TASK"; then MERGED="예"; else MERGED="아니오"; fi
  echo "| $TASK | $BR | $AHEAD | $BEHIND | $CHANGES | $RESULT | $MERGED | $WT |"
done

if [ -f "$LOGS/events.jsonl" ]; then
  echo
  echo "최근 기록 ($LOGS/events.jsonl, 마지막 5줄)"
  tail -5 "$LOGS/events.jsonl"
fi
