#!/usr/bin/env bash
# .claude/hooks/block_secrets.sh
# 비밀 정보 보호 훅(block_secrets.py)의 실행기. settings.json의 PreToolUse가 이 파일을 부른다.
#
# 하는 일: 파이썬을 골라 같은 폴더의 block_secrets.py를 돌리고, 그 종료 코드를 그대로 돌려준다.
#   0이면 통과, 2이면 막음(까닭은 표준 오류로 Claude에게 간다).
# 실패 시 닫힘: 훅이 시작하지 못하거나(127) 0·2가 아닌 코드로 끝나거나 시간을 넘기면, Claude Code는 기본으로
#   그 호출을 막지 않고 진행한다. 두 겹으로 닫는다. (1) settings.json의 이 훅에 "onFailure": "block"을 둔다
#   (Claude Code v2.1.295 이상). (2) 이 실행기가 파이썬을 찾지 못하거나 검사기가 0·2가 아닌 코드로 끝나면
#   까닭을 적고 2로 바꾼다(onFailure가 없는 판에서도 막고, 사람이 읽을 까닭을 남긴다).
# 파이썬을 고르는 순서(6장 훅, 부록 A-9-2와 같다): HOOK_PYTHON → 저장소의 .venv/Scripts/python.exe(Windows)
#   → .venv/bin/python(macOS) → PATH의 python → python3. Windows의 python3은 Microsoft Store의 실행 별칭일 수 있어 마지막이다.
# Windows: Claude Code는 이 스크립트를 Git Bash로 돌린다. CLAUDE_PROJECT_DIR은 C:\... 꼴일 수 있다.

set -u

# 경로를 슬래시 꼴로 맞춘다. 역슬래시를 슬래시로 바꾸고, Git Bash의 /c/... 꼴은 C:/... 꼴로 바꾼다.
to_slash() {
  local p="${1//\\//}"
  case "$p" in
    /*) command -v cygpath >/dev/null 2>&1 && p="$(cygpath -m "$p")" ;;
  esac
  printf '%s' "${p%/}"
}

ROOT="$(to_slash "${CLAUDE_PROJECT_DIR:-$(pwd)}")"
HOOK="$ROOT/.claude/hooks/block_secrets.py"

if [ -n "${HOOK_PYTHON:-}" ]; then
  PY="$HOOK_PYTHON"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python || command -v python3)"
fi

if [ -z "$PY" ] || [ ! -f "$HOOK" ]; then
  echo "비밀 정보 보호 훅: 파이썬이나 검사기($HOOK)를 찾지 못하여 판단할 수 없으므로 막는다." >&2
  exit 2
fi

PYTHONIOENCODING=utf-8 "$PY" "$HOOK"
code=$?
case "$code" in
  0|2) exit "$code" ;;
  *)
    echo "비밀 정보 보호 훅: 검사기가 비정상으로 끝나(종료 코드 $code) 판단할 수 없으므로 막는다." >&2
    exit 2 ;;
esac
