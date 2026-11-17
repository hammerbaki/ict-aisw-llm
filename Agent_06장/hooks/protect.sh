#!/usr/bin/env bash
# .claude/hooks/protect.sh
# PreToolUse 훅(matcher: Edit|Write). 보호 경로를 고치려는 도구 호출을 막는다.
#
# 입력: 표준 입력으로 들어오는 JSON. tool_input.file_path가 고치려는 파일의 경로이다.
# 출력: 막을 때는 표준 오류에 이유를 쓰고 종료 코드 2로 끝난다. 이 글은 Claude에게 전달된다.
#       통과할 때는 아무것도 쓰지 않고 종료 코드 0으로 끝난다.
# 보호 목록: 1) .claude/hooks/protected.txt 의 패턴(한 줄에 하나, !로 시작하면 예외)
#            2) tests/.baseline.json 에 기록된 동결 테스트 파일(2장)
# 원칙: 판단할 수 없는 입력(읽지 못한 JSON, '..'이 든 경로)을 만나면 막는다(실패 시 닫힘).
# Windows: Claude Code는 이 스크립트를 Git Bash로 돌린다. file_path는 C:\... 꼴(역슬래시)로 온다.

set -u
shopt -s nocasematch   # 경로를 대소문자 구별 없이 비교한다(Windows와 macOS의 기본 파일 시스템은 .ENV와 .env가 같은 파일)

# 경로를 슬래시 꼴로 맞춘다. 역슬래시를 슬래시로 바꾸고, Git Bash의 /c/... 꼴은 C:/... 꼴로 바꾼다.
to_slash() {
  local p="${1//\\//}"
  case "$p" in
    /*) command -v cygpath >/dev/null 2>&1 && p="$(cygpath -m "$p")" ;;
  esac
  printf '%s' "${p%/}"
}

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ROOT="$(to_slash "$PROJECT_DIR")"
LIST="$ROOT/.claude/hooks/protected.txt"
BASELINE="$ROOT/tests/.baseline.json"

# JSON을 읽을 파이썬. 저장소의 가상 환경을 먼저 쓴다(부록 A-9-2).
# Windows에서 python3은 Microsoft Store의 실행 별칭이거나 다른 판의 파이썬일 수 있으므로 마지막에 찾는다.
if [ -n "${HOOK_PYTHON:-}" ]; then
  PY="$HOOK_PYTHON"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python || command -v python3)"
fi
if [ -z "$PY" ]; then
  echo "protect.sh: 파이썬을 찾지 못하여 판단할 수 없으므로 편집을 막는다." >&2
  exit 2
fi

INPUT="$(cat)"

# tool_input.file_path를 꺼낸다. jq로는 jq -r '.tool_input.file_path // empty' 와 같다.
FILE_PATH="$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c '
import json, sys
data = json.load(sys.stdin)
sys.stdout.write(str((data.get("tool_input") or {}).get("file_path") or ""))
' 2>/dev/null)" || {
  echo "protect.sh: 훅 입력 JSON을 읽지 못하였으므로 편집을 막는다." >&2
  exit 2
}

if [ -z "$FILE_PATH" ]; then
  exit 0   # 파일 경로가 없는 호출은 이 훅이 다루지 않는다
fi

FILE_PATH="${FILE_PATH//\\//}"

# 경로 우회를 막는다: '..'이나 '.' 단계가 든 경로는 판단하지 않고 막는다.
case "/$FILE_PATH/" in
  */../*|*/./*)
    echo "protect.sh: 경로에 '..' 또는 '.' 단계가 있어 막는다: $FILE_PATH" >&2
    echo "정규화된 경로로 다시 시도하거나, 그 파일이 왜 필요한지 사람에게 보고한다." >&2
    exit 2 ;;
esac

FILE_PATH="$(to_slash "$FILE_PATH")"

# 저장소 기준의 상대 경로를 만든다. 저장소 밖의 파일은 권한 규칙이 맡는다.
case "$FILE_PATH" in
  "$ROOT"/*) REL="${FILE_PATH#"$ROOT"/}" ;;
  /*|[A-Za-z]:/*) exit 0 ;;
  *) REL="$FILE_PATH" ;;
esac

BLOCKED=""

# 1) protected.txt의 패턴과 맞추어 본다. 뒤에 나온 줄이 앞의 줄을 이긴다(.gitignore와 같다).
if [ -f "$LIST" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    line="${line%%#*}"                          # 줄의 주석을 지운다
    line="${line#"${line%%[![:space:]]*}"}"     # 앞 공백을 지운다
    line="${line%"${line##*[![:space:]]}"}"     # 뒤 공백을 지운다
    [ -z "$line" ] && continue
    if [ "${line:0:1}" = "!" ]; then
      [[ "$REL" == ${line:1} ]] && BLOCKED=""
    else
      [[ "$REL" == $line ]] && BLOCKED="protected.txt의 '$line'"
    fi
  done < "$LIST"
fi

# 2) 2장에서 동결한 테스트인지 본다. 동결 기록은 {"files": {"tests/test_x.py": "지문", ...}} 꼴이다.
if [ -z "$BLOCKED" ] && [ -f "$BASELINE" ]; then
  printf '%s' "$REL" | PYTHONIOENCODING=utf-8 "$PY" -c '
import json, sys
rel = sys.stdin.read()
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(2)
if isinstance(data, dict) and isinstance(data.get("files"), dict):
    data = data["files"]
keys = {str(k).replace("\\", "/").lower() for k in data} if isinstance(data, dict) else set()
sys.exit(0 if rel.lower() in keys else 1)
' "$BASELINE"
  case $? in
    0) BLOCKED="tests/.baseline.json에 기록된 동결 테스트" ;;
    2) case "$REL" in tests/*) BLOCKED="동결 기록(tests/.baseline.json)을 읽지 못함" ;; esac ;;
  esac
fi

if [ -n "$BLOCKED" ]; then
  echo "보호된 파일이므로 고치지 않는다: $REL (근거: $BLOCKED)" >&2
  echo "이 파일을 바꾸어야 한다면 작업을 멈추고 사람에게 까닭을 보고한다." >&2
  exit 2
fi

exit 0
