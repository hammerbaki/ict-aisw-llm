#!/usr/bin/env bash
# 운영 기록 요약 파이프라인: 수집 → 요약 → 통지
#
#   수집  logs/*.log에서 그날의 WARNING·ERROR 줄만 고른다(결정적 단계: grep)
#   요약  고른 줄을 에이전트에 파이프로 넘겨 원인별로 묶게 한다(도구 없이, 턴 1, 비용 상한)
#   통지  요약을 ops/loop/reports/digest-<날짜>.md에 쓴다(실제 알림은 이 파일을 보내는 단계로 바꾼다)
#
# 사용법 (저장소 맨 위에서)
#   bash ops/loop/digest.sh                       # 오늘 날짜, logs/ 폴더
#   DIGEST_DAY=2027-09-08 bash ops/loop/digest.sh logs
#   AGENT_CMD="python ops/loop/fake_agent.py" FAKE_SCENARIO=digest DIGEST_DAY=2027-09-08 bash ops/loop/digest.sh
#
# 종료 코드: 0 요약 또는 이상 없음을 기록함, 1 요약 실패(수동 확인 필요), 2 입력 폴더 없음

set -uo pipefail

AGENT_CMD="${AGENT_CMD:-claude}"
PYTHON="${PYTHON:-$(command -v python || command -v python3)}"   # JSON을 읽는 데 쓴다
# Windows의 파이썬이 파이프와 파일에 cp949가 아니라 UTF-8로 쓰게 한다(부록 A-4-4). macOS에서는 영향이 없다.
export PYTHONUTF8="${PYTHONUTF8:-1}"
LOG_DIR="${1:-logs}"
DAY="${DIGEST_DAY:-$(date +%F)}"
OUT_DIR="ops/loop/reports"
OUT="$OUT_DIR/digest-$DAY.md"

if [ ! -d "$LOG_DIR" ]; then
    echo "입력 폴더가 없다: $LOG_DIR" >&2
    exit 2
fi
mkdir -p "$OUT_DIR"

# 1. 수집: 그날의 경고와 오류만 (grep이 아무것도 찾지 못하면 종료 코드 1이므로 || true로 받는다)
EVENTS=$(grep -h -E "^$DAY [0-9:]+ (WARNING|ERROR) " "$LOG_DIR"/*.log | sort || true)
COUNT=$(printf '%s' "$EVENTS" | grep -c . || true)
echo "[digest] $DAY 경고·오류 ${COUNT}줄"

if [ "$COUNT" -eq 0 ]; then
    printf '# %s 운영 요약\n\n이상 없음\n' "$DAY" > "$OUT"
    echo "[digest] 이상 없음 → $OUT"
    exit 0
fi

# 2. 요약: 도구 없이(--tools ""), 한 턴, 비용 상한. 출력은 JSON 한 줄
PROMPT="표준 입력은 웹 서비스의 운영 기록 가운데 경고와 오류 줄이다. 원인별로 묶어 심각한 순서로 3줄 이내의 목록으로 요약하라. 각 줄에 건수와 시각 범위를 붙여라. 기록에 없는 원인을 지어내지 마라."
JSON=$(printf '%s\n' "$EVENTS" | $AGENT_CMD -p "$PROMPT" --output-format json --tools "" --max-turns 1 --max-budget-usd 0.10)
STATUS=$?

if [ $STATUS -ne 0 ]; then
    printf '# %s 운영 요약\n\n요약 실패: 수동 확인 필요 (에이전트 종료 코드 %s)\n' "$DAY" "$STATUS" > "$OUT"
    echo "[digest] 요약 실패(종료 코드 $STATUS) → $OUT" >&2
    exit 1
fi

# JSON에서 result를 꺼낸다. subtype이 success가 아니면 실패로 본다.
SUMMARY=$(printf '%s' "$JSON" | "$PYTHON" -c '
import json, sys
data = json.loads(sys.stdin.read().strip().splitlines()[-1])
if data.get("subtype") != "success" or not data.get("result"):
    sys.exit(1)
print(data["result"])
print("\n(비용 %.4f달러, 세션 %s)" % (data.get("total_cost_usd") or 0, data.get("session_id", "-")))
')
if [ $? -ne 0 ]; then
    printf '# %s 운영 요약\n\n요약 실패: 결과를 읽지 못함. 수동 확인 필요\n' "$DAY" > "$OUT"
    echo "[digest] 결과를 읽지 못함 → $OUT" >&2
    exit 1
fi

# 3. 통지: 파일로 남긴다
{
    printf '# %s 운영 요약\n\n' "$DAY"
    printf '경고·오류 %s줄을 요약하였다. 원문 대조는 사람이 한다.\n\n' "$COUNT"
    printf '%s\n' "$SUMMARY"
} > "$OUT"
echo "[digest] 기록 → $OUT"
exit 0
