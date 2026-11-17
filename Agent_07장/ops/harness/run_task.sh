#!/usr/bin/env bash
# 실험 한 건을 헤드리스(claude -p)로 실행하고 사건 기록(stream-json)을 남긴다.
#
# 사용: bash ops/harness/run_task.sh <실행 ID> [실험 폴더=~/agent-lab/exp]
#   예: bash ops/harness/run_task.sh T1-off-1
#
# - 작업 카드(ops/harness/작업카드/<작업>.md)의 「## 프롬프트」 아래 본문을 그대로 보낸다.
# - 두 조건에 같은 실행 옵션을 준다. 다른 것은 실험 저장소 안의 하네스 부품뿐이다.
#   --permission-mode acceptEdits : 파일 편집은 묻지 않고 허용한다(사람이 편집마다 승인하는 것을 대신한다)
#   --allowedTools : 테스트 실행과 커밋을 미리 허용한다(사람이 확인 창에서 허용했을 명령)
#   --max-turns 40 : 끝없이 돌지 않게 하는 상한
#   --model : 환경 변수 MODEL(기본값 haiku). 비교하는 동안 바꾸지 않는다
# - 실험 저장소에 plugins/*/ 가 있으면(on 조건) --plugin-dir로 그 실행에만 싣는다. 4장에서 local 범위로
#   설치한 플러그인은 원래 저장소 경로에만 켜져 있어 실험 저장소에서는 실리지 않기 때문이다.
# - 실행 전에 원래 저장소의 가상 환경을 켠다(Windows source .venv/Scripts/activate, macOS source .venv/bin/activate).
#   claude가 부르는 pytest와 .mcp.json의 python이 그 환경을 쓴다.
# - 출력: ops/harness/runs/<실행 ID>.jsonl. 같은 이름이 있으면 덮어쓰지 않고 멈춘다.
set -euo pipefail

id="${1:?실행 ID를 준다(예: T1-off-1)}"
exp="${2:-$HOME/agent-lab/exp}"
here="$(cd "$(dirname "$0")" && pwd)"
task="${id%%-*}"
card="$here/작업카드/$task.md"
dir="$exp/$id"
out="$here/runs/$id.jsonl"

[ -f "$card" ] || { echo "작업 카드가 없다: $card" >&2; exit 1; }
[ -d "$dir" ] || { echo "실험 저장소가 없다: $dir (prepare_runs.sh를 먼저 실행한다)" >&2; exit 1; }
[ -e "$out" ] && { echo "이미 기록이 있다: $out" >&2; exit 1; }
mkdir -p "$here/runs"

prompt="$(sed -n '/^## 프롬프트/,$p' "$card" | tail -n +2 | sed '/./,$!d')"   # 제목 줄과 앞의 빈 줄을 뺀다
[ -n "$prompt" ] || { echo "프롬프트 절을 찾지 못하였다: $card" >&2; exit 1; }

plugin_args=()
for p in "$dir"/plugins/*/; do
  if [ -f "$p/.claude-plugin/plugin.json" ]; then
    plugin_args+=(--plugin-dir "$p")
  fi
done

echo "실행: $id ($(date '+%H:%M:%S') 시작, 모델 ${MODEL:-haiku}, 플러그인 $(( ${#plugin_args[@]} / 2 ))개)"
cd "$dir"
claude -p "$prompt" \
  --output-format stream-json --verbose \
  --permission-mode acceptEdits \
  --allowedTools "Bash(pytest *)" "Bash(python -m pytest *)" \
                 "Bash(git add *)" "Bash(git commit *)" \
  --max-turns 40 \
  --model "${MODEL:-haiku}" \
  ${plugin_args[@]+"${plugin_args[@]}"} \
  > "$out" || echo "claude가 0이 아닌 코드로 끝났다(기록은 남겼다): $out" >&2
echo "끝: $id ($(date '+%H:%M:%S')), 기록 $(wc -l < "$out" | tr -d ' ')줄"
