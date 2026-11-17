#!/usr/bin/env bash
# CI의 eval 작업이 부르는 회귀 판정의 입구 (13장).
#
# - 12장을 마친 저장소(evals/gate.py가 있다): 12장의 실행기와 판정기를 쓴다.
#     python -m evals.run --suite all --prompt <PROMPT_SUMMARY> --ask-prompt <PROMPT_ASK> --runs 3 --tag ci
#     python -m evals.gate evals/runs/ci
#   프롬프트 판본은 저장소에 커밋된 .env.example의 PROMPT_SUMMARY, PROMPT_ASK에서 읽는다.
#   .env는 저장소에 없으므로, 운영에서 쓰는 판본을 .env.example에 적어 두어야 CI가 같은 판본을 검사한다.
# - 12장을 마치지 않은 저장소: 13장 키트의 견본 evals/run_evals.py --check 를 쓴다.
#
# 키 없이 돈다(12장의 모의 모델 sim, 또는 LLM_FAKE=1). 종료 코드 0이 아니면 CI가 실패한다.
# 쓰는 법 (저장소 폴더에서): bash ops/ci/eval_gate.sh
set -euo pipefail

PY="${PYTHON:-python}"
setting() {  # .env.example에서 KEY=값의 값을 읽는다. 없으면 빈 문자열
  grep -E "^$1=" .env.example 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '[:space:]' || true
}

if [[ -f evals/gate.py && -f evals/run.py ]]; then
  SUMMARY="$(setting PROMPT_SUMMARY)"
  ASK="$(setting PROMPT_ASK)"
  echo "== 12장 회귀 판정: summary=${SUMMARY:-summary_v1}, ask=${ASK:-ask_v1}, 반복 3회"
  "$PY" -m evals.run --suite all --prompt "${SUMMARY:-summary_v1}" --ask-prompt "${ASK:-ask_v1}" \
    --runs 3 --tag ci > /dev/null
  exec "$PY" -m evals.gate evals/runs/ci
elif [[ -f evals/run_evals.py ]]; then
  echo "== 13장 견본 회귀 평가(evals/run_evals.py)"
  exec "$PY" evals/run_evals.py --check
else
  echo "회귀 평가가 없다: 12장의 evals/ 또는 13장 기준산출물의 evals/run_evals.py를 넣는다" >&2
  exit 2
fi
