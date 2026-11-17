# ops/multi/lib.sh: 멀티 에이전트 조정 스크립트가 함께 쓰는 함수와 이름 규칙.
# 다른 스크립트가 source로 불러 쓴다. 혼자 실행하지 않는다.
#
# 이름 규칙 (이슈 ISSUE-07, 작업 T1의 경우)
#   통합 브랜치   feat/issue-07            조정자가 계획서와 인수 테스트를 올리는 브랜치
#   작업 브랜치   agent/issue-07-t1        구현 에이전트 하나가 쓰는 브랜치
#   작업 공간     .claude/worktrees/issue-07-t1   git worktree (저장소 맨 위 기준)
#   인계 문서     docs/운영/인계/ISSUE-07/  계획서, 작업 카드(T1_카드.md), 결과 보고(T1_보고.md)
#   실행 기록     ops/multi/logs/ISSUE-07/  events.jsonl(누가 언제 무엇을 했는가), 판정, 에이전트 출력

set -o pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "오류: git 저장소 안에서 실행한다" >&2; exit 2; }
# worktree 안에서 실행해도 기본 작업 공간(main worktree)을 기준으로 삼는다.
MAIN_ROOT="$(git -C "$ROOT" worktree list --porcelain | sed -n '1s/^worktree //p')"
cd "$MAIN_ROOT" || exit 2

LOG_BASE="ops/multi/logs"
# 작업 공간을 두는 폴더. 스크립트(prepare.sh)는 .claude/worktrees에 만든다.
# Orca처럼 다른 도구가 만든 작업 공간은 task_dir가 작업 브랜치 이름으로 찾는다(아래).
# MULTI_WT_BASE는 그 폴더 아래에 issue-07-t1 꼴의 이름으로 있을 때만 쓰는 옛 방식이다.
WT_BASE="${MULTI_WT_BASE:-.claude/worktrees}"
# 판정 명령. 기본은 기본 작업 공간의 가상 환경으로 pytest를 돌린다(작업 공간마다 가상 환경을 따로 만들지 않는다).
# 가상 환경을 켜지 않고도 돌도록 해석기를 직접 고른다. Windows는 .venv/Scripts/python.exe,
# macOS와 리눅스는 .venv/bin/python이다(부록 A-9-2). 둘 다 없으면 가상 환경을 켠 셸의 python을 쓴다.
if [ -x "$MAIN_ROOT/.venv/Scripts/python.exe" ]; then
  DEFAULT_PY="$MAIN_ROOT/.venv/Scripts/python.exe"
elif [ -x "$MAIN_ROOT/.venv/bin/python" ]; then
  DEFAULT_PY="$MAIN_ROOT/.venv/bin/python"
else
  DEFAULT_PY="python"
fi
PY="${MULTI_PY:-$DEFAULT_PY}"
JUDGE_CMD="${JUDGE_CMD:-$PY -m pytest -q}"

die() { echo "오류: $*" >&2; exit 2; }

issue_slug() {            # ISSUE-07 -> issue-07
  echo "$1" | tr '[:upper:]' '[:lower:]'
}
task_slug() {             # T1 -> t1
  echo "$1" | tr '[:upper:]' '[:lower:]'
}
integration_branch() { echo "feat/$(issue_slug "$1")"; }
task_branch()        { echo "agent/$(issue_slug "$1")-$(task_slug "$2")"; }
# 작업 공간의 경로. 찾는 순서:
#   1. MULTI_WT_BASE를 주었으면 그 폴더 아래의 issue-07-t1
#   2. 스크립트가 만드는 자리 .claude/worktrees/issue-07-t1이 있으면 그것
#   3. 작업 브랜치(agent/issue-07-t1)를 꺼내 둔 git worktree가 있으면 그 경로(git worktree list --porcelain)
#      Orca처럼 다른 도구가 만든 작업 공간은 폴더 이름과 위치가 도구마다 다르므로 브랜치 이름으로 찾는다
#   4. 어느 것도 없으면 .claude/worktrees/issue-07-t1(prepare.sh가 여기에 만든다)
task_dir() {
  local slug br found
  slug="$(issue_slug "$1")-$(task_slug "$2")"
  if [ -n "${MULTI_WT_BASE:-}" ]; then echo "$MULTI_WT_BASE/$slug"; return; fi
  if [ -d "$WT_BASE/$slug" ]; then echo "$WT_BASE/$slug"; return; fi
  br="$(task_branch "$1" "$2")"
  found="$(git worktree list --porcelain | awk -v want="branch refs/heads/$br" \
    'substr($0, 1, 9) == "worktree " { path = substr($0, 10) } $0 == want { print path; exit }')"
  if [ -n "$found" ]; then echo "$found"; else echo "$WT_BASE/$slug"; fi
}
handoff_dir()        { echo "docs/운영/인계/$1"; }
card_path()          { echo "$(handoff_dir "$1")/$2_카드.md"; }
report_path()        { echo "$(handoff_dir "$1")/$2_보고.md"; }
log_dir()            { echo "$LOG_BASE/$1"; }

# 실행 기록에 한 줄을 더한다: log_event 이슈 행위자 사건 [작업] [내용]
# 형식은 JSON Lines이다. 내용에 큰따옴표와 역슬래시가 들어가면 바꾸어 적는다.
log_event() {
  local issue="$1" actor="$2" event="$3" task="${4:-}" detail="${5:-}"
  local dir; dir="$(log_dir "$issue")"
  mkdir -p "$dir"
  detail="${detail//\\//}"
  detail="${detail//\"/\'}"
  printf '{"time":"%s","issue":"%s","actor":"%s","event":"%s","task":"%s","detail":"%s"}\n' \
    "$(date '+%Y-%m-%dT%H:%M:%S')" "$issue" "$actor" "$event" "$task" "$detail" >> "$dir/events.jsonl"
}

# 작업 카드의 「- 소유 파일:」 줄에서 역따옴표로 감싼 경로를 한 줄에 하나씩 꺼낸다.
# 경로가 /로 끝나면 그 폴더 아래 전체를 뜻한다.
owned_files() {
  local card="$1"
  grep -m1 '^- 소유 파일:' "$card" | grep -o '`[^`]*`' | tr -d '`'
}

# 작업 카드의 「- 공유 파일:」 줄의 경로. 여러 작업이 함께 고쳐도 되는 파일(끝에 한 줄을 더하는 기록 등)이다.
# 범위 판정은 소유 파일처럼 받아들인다. 두 작업이 같은 자리를 고치면 병합할 때 충돌하므로,
# prepare.sh는 거부하지 않고 알리기만 한다. 줄이 없으면 아무것도 내지 않는다.
shared_files() {
  local card="$1"
  grep -m1 '^- 공유 파일:' "$card" | grep -o '`[^`]*`' | tr -d '`'
}

# 작업 카드의 「- 인수 테스트:」 줄의 경로. 카드는 통합 브랜치에서 읽는다.
acceptance_of() {
  git show "$(integration_branch "$1"):$(card_path "$1" "$2")" 2>/dev/null \
    | grep -m1 '^- 인수 테스트:' | grep -o '`[^`]*`' | tr -d '`'
}

# 통합 브랜치의 인계 폴더에 카드가 있는 작업 이름(T1, T2 ...)
all_tasks() {
  git -c core.quotepath=false ls-tree --name-only "$(integration_branch "$1")" "$(handoff_dir "$1")/" \
    | sed -n 's#.*/\(T[0-9][0-9]*\)_카드\.md$#\1#p'
}

# 작업이 merge.sh로 통합 브랜치에 병합되었는가.
# 커밋이 하나도 없는 작업 브랜치도 git으로는 「조상」이므로, merge.sh가 남긴 병합 기록과 함께 본다.
is_merged() {
  local issue="$1" task="$2" br
  br="$(task_branch "$issue" "$task")"
  git merge-base --is-ancestor "$br" "$(integration_branch "$issue")" 2>/dev/null \
    && grep -q "\"event\":\"merged\",\"task\":\"$task\"" "$(log_dir "$issue")/events.jsonl" 2>/dev/null
}

# 아직 통합 브랜치에 들어오지 않은 다른 작업의 인수 테스트를 빼는 pytest 인자를 만든다.
# 사용: ignore_args 이슈 판정할작업...   예) ignore_args ISSUE-07 T1  ->  --ignore=tests/test_web_export.py
# 빼는 것은 「작업 브랜치가 있고, 아직 병합되지 않은」 작업의 인수 테스트뿐이다.
# 작업마다 인수 테스트를 나누어 두었기 때문에, 한 작업만 병합된 상태에서도 나머지 테스트로 판정할 수 있다.
ignore_args() {
  local issue="$1"; shift
  local task keep test br
  for task in $(all_tasks "$issue"); do
    keep=no
    for k in "$@"; do [ "$k" = "$task" ] && keep=yes; done
    [ "$keep" = yes ] && continue
    br="$(task_branch "$issue" "$task")"
    git rev-parse --verify --quiet "$br" >/dev/null || continue
    is_merged "$issue" "$task" && continue
    for test in $(acceptance_of "$issue" "$task"); do
      printf -- '--ignore=%s ' "$test"
    done
  done
}

# 경로 하나가 소유 목록에 드는지 본다.
is_owned() {
  local path="$1"; shift
  local own
  for own in "$@"; do
    if [ "$path" = "$own" ]; then return 0; fi
    case "$own" in
      */) case "$path" in "$own"*) return 0 ;; esac ;;
    esac
  done
  return 1
}

# 기본 작업 공간이 깨끗한지 본다. 실행 기록 폴더의 변경은 빼고 본다.
require_clean_main() {
  local dirty
  dirty="$(git status --porcelain --untracked-files=normal | grep -v " $LOG_BASE/" || true)"
  if [ -n "$dirty" ]; then
    echo "$dirty" >&2
    die "기본 작업 공간에 커밋하지 않은 변경이 있다. 커밋하거나 되돌린 뒤 다시 실행한다"
  fi
}

# 계획서에 사람의 승인 줄이 있는지 본다: 「- 승인: 이름, 날짜」
require_approval() {
  local issue="$1" branch plan
  branch="$(integration_branch "$issue")"
  plan="$(handoff_dir "$issue")/계획서.md"
  git show "$branch:$plan" >/dev/null 2>&1 || die "$branch에 $plan이 없다"
  if ! git show "$branch:$plan" | grep -Eq '^- 승인: *[^「 ].*'; then
    die "계획서에 사람의 승인 줄(- 승인: 이름, 날짜)이 없다. 승인 전에는 작업을 나누어 주지 않는다"
  fi
}
