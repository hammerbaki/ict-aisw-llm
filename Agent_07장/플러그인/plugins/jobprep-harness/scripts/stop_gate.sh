#!/usr/bin/env bash
# .claude/hooks/stop_gate.sh
# Stop 훅. Claude가 응답을 마치려 할 때 전체 테스트를 돌리고, 실패하면 한 번 더 일하게 한다.
#
# 입력: 표준 입력으로 들어오는 JSON. stop_hook_active가 true이면 이미 이 훅 때문에 이어 가는 중이다.
# 출력: 테스트가 실패하면 {"decision": "block", "reason": "..."} 를 표준 출력에 쓰고 종료 코드 0.
#       reason은 Claude에게 다음 지시로 전달된다. 통과하면 아무것도 쓰지 않는다.
# 무한 반복 방지: stop_hook_active가 true이면 결과와 관계없이 멈춤을 허용한다.
#                 그래서 이 훅이 이어 가게 하는 것은 응답 한 번에 한 번뿐이다.
# 권장 위치: 공유 설정이 아니라 개인 설정(.claude/settings.local.json). 6절을 본다.

set -u

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
ACTIVE="$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c '
import json, sys
data = json.load(sys.stdin)
sys.stdout.write("true" if data.get("stop_hook_active") else "false")
' 2>/dev/null)" || ACTIVE="true"   # 입력을 읽지 못하면 멈춤을 허용한다(반복을 만들지 않는다)

if [ "$ACTIVE" = "true" ]; then
  echo "stop_gate.sh: 이미 한 번 이어 가게 하였으므로 멈춤을 허용한다." >&2
  exit 0
fi

cd "$ROOT" || exit 0
OUT="$(LLM_FAKE=1 PYTHONIOENCODING=utf-8 "$PY" -m pytest -q --no-header --tb=short --show-capture=no -p no:cacheprovider 2>&1)"
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  exit 0
fi

# 실패 요약을 reason에 담아 JSON으로 낸다. 문자열을 손으로 이어 붙이지 않고 JSON 부호기로 만든다.
printf '%s' "$OUT" | tail -n 15 | PYTHONIOENCODING=utf-8 "$PY" -c '
import json, sys
tail = sys.stdin.read()
reason = ("pytest가 통과하지 않은 상태로 끝내려 한다. 실패한 테스트를 고친다. "
          "테스트 파일은 고치지 않는다. 고칠 수 없으면 까닭을 보고하고 멈춘다.\n" + tail)
sys.stdout.write(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
'
exit 0
