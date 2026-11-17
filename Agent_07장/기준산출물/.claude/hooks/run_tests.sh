#!/usr/bin/env bash
# .claude/hooks/run_tests.sh
# PostToolUse 훅(matcher: Edit|Write). 파이썬 파일을 고친 직후 문법 검사와 관련 테스트를 돌린다.
#
# 입력: 표준 입력으로 들어오는 JSON. tool_input.file_path가 방금 고친 파일이다.
# 출력: 검사가 실패하면 표준 오류에 실패 내용을 쓰고 종료 코드 2로 끝난다. 이 글은 Claude에게 전달된다.
#       통과하면 종료 코드 0으로 끝난다. 이때의 표준 출력은 디버그 기록에만 남는다.
# 주의: PostToolUse는 도구가 이미 실행된 뒤에 돈다. 편집을 되돌리지 못하고, 알려 줄 뿐이다.

set -u
shopt -s nocasematch   # 경로를 대소문자 구별 없이 비교한다(protect.sh와 같다)

# 경로를 슬래시 꼴로 맞춘다(protect.sh와 같다). Git Bash의 /c/... 꼴은 C:/... 꼴로 바꾼다.
to_slash() {
  local p="${1//\\//}"
  case "$p" in
    /*) command -v cygpath >/dev/null 2>&1 && p="$(cygpath -m "$p")" ;;
  esac
  printf '%s' "${p%/}"
}

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ROOT="$(to_slash "$PROJECT_DIR")"

# 테스트에 쓸 파이썬. 훅은 가상 환경을 켜지 않은 셸에서 돌므로 저장소의 .venv를 직접 가리킨다(부록 A-9-2).
# .venv/Scripts/python.exe(Windows)를 먼저, 없으면 .venv/bin/python(macOS·리눅스)을 찾는다.
if [ -n "${JOBPREP_PYTHON:-}" ]; then
  PY="$JOBPREP_PYTHON"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"   # Windows의 가상 환경
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"           # macOS·리눅스의 가상 환경
else
  PY="$(command -v python || command -v python3)"
fi

INPUT="$(cat)"
FILE_PATH="$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c '
import json, sys
data = json.load(sys.stdin)
sys.stdout.write(str((data.get("tool_input") or {}).get("file_path") or ""))
' 2>/dev/null)" || exit 0   # 입력을 읽지 못하면 검사하지 않는다(이 훅은 막는 훅이 아니다)

FILE_PATH="$(to_slash "$FILE_PATH")"

case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;   # 파이썬 파일이 아니면 검사하지 않는다
esac

case "$FILE_PATH" in
  "$ROOT"/*) REL="${FILE_PATH#"$ROOT"/}" ;;
  *) exit 0 ;;   # 저장소 밖의 파일은 검사하지 않는다
esac

# 1. 문법 검사: 테스트보다 빠르고, 실패 위치를 정확히 알려 준다.
if ! ERR="$(PYTHONIOENCODING=utf-8 "$PY" -m py_compile "$FILE_PATH" 2>&1)"; then
  {
    echo "문법 오류: $REL"
    printf '%s\n' "$ERR" | tail -n 6
    echo "이 파일의 문법 오류부터 고친다."
  } >&2
  exit 2
fi

# 2. 동결 검사(2장의 tools/test_guard.py가 있을 때만): 동결된 테스트와 테스트 설정이 그대로인가.
#    Bash 명령 등 protect.sh를 거치지 않은 길로 테스트가 바뀐 것도 여기서 드러난다.
if [ -f "$ROOT/tools/test_guard.py" ] && [ -f "$ROOT/tests/.baseline.json" ]; then
  if ! GUARD="$(cd "$ROOT" && PYTHONIOENCODING=utf-8 "$PY" tools/test_guard.py check 2>&1)"; then
    {
      echo "동결 검사 실패: 동결 뒤에 테스트나 테스트 설정이 바뀌거나 더해졌다."
      printf '%s\n' "$GUARD" | tail -n 10
      echo "테스트를 바꾸거나 더하는 것은 사람이 정한다(2장의 freeze --update). 멈추고 사람에게 보고한다."
    } >&2
    exit 2
  fi
fi

# 3. 고친 파일과 관련된 테스트를 고른다. 모듈을 더하면 이 표에 한 줄을 더한다.
case "$REL" in
  tests/test_*.py)  CANDIDATES="$REL" ;;
  api/jobs.py)      CANDIDATES="tests/test_jobs.py" ;;
  api/summary.py)   CANDIDATES="tests/test_summary.py" ;;
  api/ask.py)       CANDIDATES="tests/test_ask.py" ;;
  api/llm.py)       CANDIDATES="tests/test_llm.py tests/test_summary.py tests/test_ask.py" ;;
  rag/*.py)         CANDIDATES="tests/test_rag.py tests/test_ask.py" ;;
  *)                CANDIDATES="tests" ;;   # main.py, conftest.py, 그 밖의 파일은 전체를 돌린다
esac

TARGETS=""
for target in $CANDIDATES; do
  [ -e "$ROOT/$target" ] && TARGETS="$TARGETS $target"
done
[ -z "$TARGETS" ] && TARGETS=" tests"

cd "$ROOT" || exit 0
OUT="$(LLM_FAKE=1 PYTHONIOENCODING=utf-8 "$PY" -m pytest -q -x --no-header --tb=short --show-capture=no -p no:cacheprovider $TARGETS 2>&1)"
STATUS=$?

if [ "$STATUS" -eq 0 ] || [ "$STATUS" -eq 5 ]; then   # 5: 모을 테스트가 없음
  echo "run_tests.sh: $REL →$TARGETS 통과"
  exit 0
fi

{
  echo "테스트 실패: $REL 을 고친 뒤$TARGETS 이(가) 통과하지 않는다."
  printf '%s\n' "$OUT" | tail -n 25
  echo "테스트 파일을 고쳐 통과시키지 말고 구현을 고친다."
} >&2
exit 2
