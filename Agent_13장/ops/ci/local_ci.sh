#!/usr/bin/env bash
# CI(.github/workflows/ci.yml)의 네 작업이 부르는 명령을 같은 순서로 이 컴퓨터에서 돌린다 (13장).
# 푸시하기 전에 돌려 보면 GitHub에서 기다렸다가 실패하는 일이 줄어든다.
# ci.yml의 run: 줄을 고치면 이 파일도 함께 고친다.
#
# 쓰는 법 (저장소 폴더에서, 가상 환경을 켠 상태로)
#   bash ops/ci/local_ci.sh            지금 가상 환경으로 돌린다
#   bash ops/ci/local_ci.sh --fresh    새 가상 환경(임시 폴더)을 만들어 잠금 파일로 설치한 뒤 돌린다(러너와 가장 비슷하다)
# 파이썬은 PYTHON이 있으면 그것을, 없으면 켠 가상 환경의 python을 쓴다(Windows Git Bash에는 python3이 없다).
set -uo pipefail

export LLM_FAKE=1 EMBED_BACKEND=fallback PYTHONIOENCODING=utf-8
PY="${PYTHON:-$(command -v python || command -v python3)}"
if [[ "${1:-}" == "--fresh" ]]; then
  VENV="$(mktemp -d)/venv"
  "$PY" -m venv "$VENV"
  # Windows는 Scripts/python.exe, macOS·리눅스는 bin/python (부록 A-9-2)
  if [[ -x "$VENV/Scripts/python.exe" ]]; then PY="$VENV/Scripts/python.exe"; else PY="$VENV/bin/python"; fi
  echo "== 새 가상 환경: $VENV"
  "$PY" -m pip install --quiet --disable-pip-version-check --require-hashes -r requirements.lock || exit 1
fi

failed=()
step() {  # $1: 작업 이름, 나머지: 명령
  local job="$1"; shift
  echo "== [$job] $*"
  if "$@"; then echo "   -> 통과"; else echo "   -> 실패"; failed+=("$job"); fi
}

step test    "$PY" -m pytest -q -p no:cacheprovider
step eval    env PYTHON="$PY" bash ops/ci/eval_gate.sh
step secrets "$PY" security/scan_secrets.py
step rules   "$PY" ops/rules/check_code_rules.py
step rules   "$PY" ops/version/check_pins.py

if (( ${#failed[@]} )); then
  echo "실패한 작업: ${failed[*]}"
  exit 1
fi
echo "네 작업(test, eval, secrets, rules) 모두 통과"
