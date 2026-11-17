#!/usr/bin/env bash
# ops/multi/judge.sh: 작업 브랜치 하나를 판정한다(테스트 에이전트와 검토 에이전트의 자리).
#
# 사용법 (저장소 맨 위에서)
#   bash ops/multi/judge.sh ISSUE-07 T1
#
# 판정 항목 (모두 통과해야 「통과」)
#   1. 커밋   작업 공간에 커밋하지 않은 변경이 없다
#   2. 범위   통합 브랜치와 갈라진 뒤 바뀐 파일이 모두 카드의 소유 파일(또는 공유 파일)이다
#   3. 동결   통합 브랜치에 있던 tests/의 파일을 고치거나 지우지 않았다
#   4. 보고   결과 보고 파일이 작업 브랜치에 있다
#   5. 테스트 JUDGE_CMD(기본: pytest -q)가 작업 공간에서 통과한다
#   6. 검토   REVIEW_CMD의 출력에 「판정: 통과」가 있다
#              기본은 규칙 검토기(ops/multi/rule_review.py). LLM 검토자는
#              REVIEW_CMD="claude -p --agent reviewer" 처럼 바꾸어 넣는다
# 결과: ops/multi/logs/<이슈>/판정_<작업>.md(마지막 판정)와 판정_<작업>_<커밋 7자리>.md(그 커밋의 판정).
#       판정한 커밋을 적어 두고, merge.sh가 대조한다.
# 종료 코드: 통과 0, 거부 1, 시작 조건 실패 2.

source "$(dirname "$0")/lib.sh"

[ $# -eq 2 ] || die "사용법: bash ops/multi/judge.sh <이슈> <작업>"
ISSUE="$1"; TASK="$2"
BASE="$(integration_branch "$ISSUE")"
BR="$(task_branch "$ISSUE" "$TASK")"
DIR="$(task_dir "$ISSUE" "$TASK")"
CARD="$(card_path "$ISSUE" "$TASK")"
REPORT="$(report_path "$ISSUE" "$TASK")"
REVIEW_CMD="${REVIEW_CMD:-$PY ops/multi/rule_review.py}"
LOGS="$(log_dir "$ISSUE")"
OUTFILE="$LOGS/판정_$TASK.md"
[ -d "$DIR" ] || die "$DIR가 없다"
mkdir -p "$LOGS"

HEAD_SHA="$(git rev-parse "$BR")"
mapfile -t OWNED < <(git show "$BASE:$CARD" | grep -m1 '^- 소유 파일:' | grep -o '`[^`]*`' | tr -d '`')
[ "${#OWNED[@]}" -gt 0 ] || die "$CARD에서 소유 파일을 읽지 못하였다"
mapfile -t SHARED < <(git show "$BASE:$CARD" | grep -m1 '^- 공유 파일:' | grep -o '`[^`]*`' | tr -d '`')

declare -a ROWS=()
VERDICT="통과"
row() {   # row 항목 결과 내용
  ROWS+=("| $1 | $2 | $3 |")
  [ "$2" = "통과" ] || VERDICT="거부"
}

# 1. 커밋
DIRTY="$(git -C "$DIR" status --porcelain | head -5 | tr '\n' ' ')"
if [ -z "$DIRTY" ]; then row "커밋" "통과" "작업 공간이 깨끗하다"
else row "커밋" "거부" "커밋하지 않은 변경: $DIRTY"; fi

# 2. 범위
mapfile -t CHANGED < <(git -c core.quotepath=false diff --name-only "$BASE...$BR")
OUTSIDE=()
NSHARED=0
for F in "${CHANGED[@]}"; do
  if is_owned "$F" "${OWNED[@]}"; then continue; fi
  if [ "${#SHARED[@]}" -gt 0 ] && is_owned "$F" "${SHARED[@]}"; then NSHARED=$((NSHARED + 1)); continue; fi
  OUTSIDE+=("$F")
done
if [ "${#CHANGED[@]}" -eq 0 ]; then row "범위" "거부" "바뀐 파일이 없다"
elif [ "${#OUTSIDE[@]}" -eq 0 ] && [ "$NSHARED" -eq 0 ]; then row "범위" "통과" "바뀐 파일 ${#CHANGED[@]}개가 모두 소유 파일이다"
elif [ "${#OUTSIDE[@]}" -eq 0 ]; then row "범위" "통과" "바뀐 파일 ${#CHANGED[@]}개가 모두 소유 파일이다(공유 파일 ${NSHARED}개 포함)"
else row "범위" "거부" "소유 파일 밖: ${OUTSIDE[*]}"; fi

# 3. 동결
mapfile -t TOUCHED < <(git -c core.quotepath=false diff --name-only --diff-filter=MDR "$BASE...$BR" -- tests/)
if [ "${#TOUCHED[@]}" -eq 0 ]; then row "동결" "통과" "기존 테스트 파일이 그대로이다"
else row "동결" "거부" "기존 테스트를 고치거나 지움: ${TOUCHED[*]}"; fi

# 4. 보고
if git cat-file -e "$BR:$REPORT" 2>/dev/null; then row "보고" "통과" "$REPORT"
else row "보고" "거부" "$REPORT가 작업 브랜치에 없다"; fi

# 5. 테스트 (아직 병합되지 않은 다른 작업의 인수 테스트는 뺀다)
IGNORES="$(ignore_args "$ISSUE" "$TASK")"
TEST_OUT="$( cd "$DIR" && $JUDGE_CMD $IGNORES 2>&1 )"; TEST_CODE=$?
TEST_OUT="${TEST_OUT//$'\r'/}"   # Windows의 파이썬은 줄 끝을 CRLF로 내보낸다. 판정 파일은 LF로 쓴다
TEST_LAST="$(printf '%s\n' "$TEST_OUT" | grep -v '^\s*$' | tail -1)"
if [ "$TEST_CODE" -eq 0 ]; then row "테스트" "통과" "$TEST_LAST"
else row "테스트" "거부" "종료 코드 $TEST_CODE: $TEST_LAST"; fi

# 6. 검토
read -r -a RCMD <<< "$REVIEW_CMD"
REVIEW_PROMPT="표준 입력은 통합 브랜치 $BASE와 작업 브랜치 $BR의 차이(git diff $BASE...$BR)이다. 작업 카드는 $CARD이다. 첫 줄에 「판정: 통과」 또는 「판정: 거부」를 쓰고, 문제마다 한 줄씩 파일:줄 — 문제 — 근거를 쓴다."
# 검토자에게 git 명령 권한을 주지 않고 차이를 표준 입력으로 넘긴다(검토자는 읽기 도구만 있으면 된다).
REVIEW_OUT="$( cd "$DIR" && git -c core.quotepath=false diff "$BASE...$BR" \
  | MULTI_BASE="$BASE" MULTI_BRANCH="$BR" "${RCMD[@]}" "$REVIEW_PROMPT" 2>&1 )"
REVIEW_OUT="${REVIEW_OUT//$'\r'/}"
if printf '%s\n' "$REVIEW_OUT" | grep -q '판정: 통과'; then row "검토" "통과" "$(printf '%s\n' "$REVIEW_OUT" | head -1)"
else row "검토" "거부" "$(printf '%s\n' "$REVIEW_OUT" | grep -v '^판정' | head -3 | tr '\n' ' ')"; fi

{
  echo "# 판정: $ISSUE $TASK"
  echo
  echo "- 판정: $VERDICT"
  echo "- 작업 브랜치: \`$BR\`"
  echo "- 판정한 커밋: \`$HEAD_SHA\`"
  echo "- 시각: $(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo "| 항목 | 결과 | 내용 |"
  echo "|---|---|---|"
  printf '%s\n' "${ROWS[@]}"
  echo
  echo "## 검토 출력"
  echo
  echo '```text'
  printf '%s\n' "$REVIEW_OUT"
  echo '```'
} > "$OUTFILE"
# 시도마다의 판정을 남긴다. 판정_T1.md는 늘 마지막 판정이고, 판정_T1_<커밋 7자리>.md는 그 커밋의 판정이다.
cp "$OUTFILE" "$LOGS/판정_${TASK}_${HEAD_SHA:0:7}.md"

echo "판정  $TASK  $VERDICT  ($OUTFILE)"
printf '%s\n' "${ROWS[@]}"
log_event "$ISSUE" "judge" "judged" "$TASK" "verdict=$VERDICT commit=${HEAD_SHA:0:7}"
[ "$VERDICT" = "통과" ]
