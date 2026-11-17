#!/usr/bin/env bash
# .claude/hooks/check_hooks.sh
# 훅 스크립트를 견본 입력(samples/*.json)으로 실행해 종료 코드와 출력을 확인한다.
# Claude Code와 모델 없이 돈다. 훅을 고칠 때마다 이 점검을 먼저 통과시킨다.
#
# 실행: bash .claude/hooks/check_hooks.sh        (저장소 폴더에서)
# 결과: 사례마다 PASS 또는 FAIL, 마지막 줄에 합계. FAIL이 하나라도 있으면 종료 코드 1.

set -u
shopt -u patsub_replacement 2>/dev/null   # bash 5.2 이상: 치환 글의 &를 글자 그대로 둔다

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HOOKS_DIR/../.." && pwd)"
# 윈도의 Git Bash에서는 C:/... 꼴로 바꾼다. Claude Code가 훅에 넘기는 경로의 꼴과 맞추기 위해서다.
if command -v cygpath >/dev/null 2>&1; then
  ROOT="$(cygpath -m "$ROOT")"
fi
SAMPLES="$HOOKS_DIR/samples"

# 테스트를 돌릴 파이썬: 저장소의 가상 환경(부록 A-9-2). 임시 사본에서도 같은 파이썬을 쓰게 한다.
if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  export JOBPREP_PYTHON="$ROOT/.venv/Scripts/python.exe"   # Windows
elif [ -x "$ROOT/.venv/bin/python" ]; then
  export JOBPREP_PYTHON="$ROOT/.venv/bin/python"           # macOS·리눅스
else
  echo "저장소의 가상 환경(.venv)을 찾지 못하였다. 부록 A-9의 순서로 .venv를 만든 뒤 다시 실행한다." >&2
  exit 1
fi

PASS=0
FAIL=0

# run_case 이름 스크립트 견본 기대종료코드 기대문구 [프로젝트폴더]
#   기대문구가 "-"이면 출력을 검사하지 않고, "!글"이면 그 글이 출력에 없어야 한다.
run_case() {
  local name="$1" script="$2" sample="$3" want="$4" expect="$5" proj="${6:-$ROOT}"
  local input out code ok
  local projw="${proj//\//\\}"                 # C:/... 를 Windows 꼴 C:\... 로
  projw="${projw//\\/\\\\}"                    # JSON 문자열 안에서는 역슬래시를 두 번 쓴다
  input="$(cat "$SAMPLES/$sample")"
  input="${input//__PROJECT_WIN__/$projw}"     # Claude Code가 Windows에서 넘기는 꼴(역슬래시)
  input="${input//__PROJECT__/$proj}"          # 견본의 자리 표시를 실제 저장소 경로로 바꾼다
  out="$(printf '%s' "$input" | CLAUDE_PROJECT_DIR="$proj" bash "$HOOKS_DIR/$script" 2>&1)"
  code=$?
  ok=1
  [ "$code" = "$want" ] || ok=0
  case "$expect" in
    -) ;;
    !*) printf '%s' "$out" | grep -qF -- "${expect:1}" && ok=0 ;;
    *) printf '%s' "$out" | grep -qF -- "$expect" || ok=0 ;;
  esac
  if [ "$ok" = 1 ]; then
    printf 'PASS  %-28s 종료 코드 %s\n' "$name" "$code"
    PASS=$((PASS + 1))
  else
    printf 'FAIL  %-28s 종료 코드 %s (기대 %s, 기대 문구 %s)\n' "$name" "$code" "$want" "$expect"
    printf '%s\n' "$out" | head -n 6 | sed 's/^/      | /'
    FAIL=$((FAIL + 1))
  fi
}

echo "== protect.sh (PreToolUse)"
run_case "보호: .env 편집"            protect.sh pre_edit_env.json          2 "보호된 파일"
run_case "허용: .env.example 편집"    protect.sh pre_edit_env_example.json  0 -
run_case "보호: 동결 기록"            protect.sh pre_write_baseline.json    2 "tests/.baseline.json"
run_case "보호: 동결된 테스트"        protect.sh pre_edit_frozen_test.json  2 "동결 테스트"
run_case "허용: 새 테스트 파일"       protect.sh pre_write_new_test.json    0 -
run_case "허용: api/jobs.py 편집"     protect.sh pre_edit_api.json          0 -
run_case "보호: '..' 경로 우회"       protect.sh pre_edit_traversal.json    2 "'..'"
run_case "보호: Windows 꼴 .ENV"      protect.sh pre_edit_env_windows.json  2 "보호된 파일"
run_case "보호: 공고 데이터"          protect.sh pre_write_jobs_data.json   2 "data/jobs.json"
run_case "보호: 깨진 입력"            protect.sh pre_broken.json            2 "JSON"

# 실패하는 상태는 저장소를 건드리지 않도록 임시 사본에서 만든다.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -r "$ROOT/api" "$ROOT/rag" "$ROOT/tests" "$ROOT/data" "$ROOT/prompts" "$ROOT/pytest.ini" "$TMP/"
if command -v cygpath >/dev/null 2>&1; then
  TMPP="$(cygpath -m "$TMP")"
else
  TMPP="$TMP"
fi
BROKEN="$TMP/broken"; mkdir -p "$BROKEN"
cp -r "$TMP/api" "$TMP/rag" "$TMP/tests" "$TMP/data" "$TMP/prompts" "$TMP/pytest.ini" "$BROKEN/"
printf '\ndef broken(:\n    pass\n' >> "$BROKEN/api/jobs.py"                         # 문법 오류
sed 's/^MAX_ITEMS = 5/MAX_ITEMS = 0/' "$TMP/api/summary.py" > "$TMP/summary.tmp" \
  && mv "$TMP/summary.tmp" "$TMP/api/summary.py"                                     # 요약 항목이 사라지는 결함(sed -i는 macOS와 달라 쓰지 않는다)

echo "== run_tests.sh (PostToolUse)"
run_case "건너뜀: README.md 편집"     run_tests.sh post_edit_readme.json    0 "!통과"
run_case "통과: api/jobs.py 편집"     run_tests.sh post_edit_jobs.json      0 "통과"
run_case "실패: 문법 오류"            run_tests.sh post_edit_jobs.json      2 "문법 오류"   "$TMPP/broken"
run_case "실패: 관련 테스트"          run_tests.sh post_edit_summary.json   2 "테스트 실패" "$TMPP"

# 2장의 동결 검사기가 있으면, 동결된 테스트를 바꾼 사본에서 동결 검사가 실패를 알리는지 본다.
if [ -f "$ROOT/tools/test_guard.py" ] && [ -f "$ROOT/tests/.baseline.json" ]; then
  GUARDED="$TMP/guarded"; mkdir -p "$GUARDED"
  cp -r "$ROOT/api" "$ROOT/rag" "$ROOT/tests" "$ROOT/data" "$ROOT/prompts" "$ROOT/pytest.ini" "$ROOT/tools" "$GUARDED/"
  printf '\n# 동결 뒤에 더한 줄\n' >> "$GUARDED/tests/test_jobs.py"
  run_case "실패: 동결 검사"            run_tests.sh post_edit_jobs.json      2 "동결 검사 실패" "$TMPP/guarded"
else
  echo "(건너뜀) 실패: 동결 검사 — tools/test_guard.py 또는 tests/.baseline.json이 없다"
fi

echo "== stop_gate.sh (Stop)"
run_case "멈춤 허용: 테스트 통과"     stop_gate.sh stop.json                0 '!"decision"'
run_case "이어 가기: 테스트 실패"     stop_gate.sh stop.json                0 '"decision": "block"' "$TMPP"
run_case "멈춤 허용: 이미 이어 가는 중" stop_gate.sh stop_active.json       0 '!"decision"'          "$TMPP"

echo "== 결과: 통과 $PASS, 실패 $FAIL"
[ "$FAIL" -eq 0 ]
