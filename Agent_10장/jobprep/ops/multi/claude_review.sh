#!/usr/bin/env bash
# ops/multi/claude_review.sh: 실제 Claude Code(헤드리스)로 검토 에이전트를 실행하는 감싸개.
# judge.sh가 작업 공간 안에서 부르고, 표준 입력으로 차이(git diff 통합...작업)를, 마지막 인자로 지시문을 넘긴다.
#
#   REVIEW_CMD="bash ops/multi/claude_review.sh" bash ops/multi/judge.sh ISSUE-07 T1
#
# 검토자(reviewer.md)의 도구는 Read, Grep, Glob뿐이다. 차이를 표준 입력으로 받으므로 git 권한이 필요 없다.
# 판정은 출력의 「판정: 통과」 줄로 한다. 이 감싸개는 텍스트 출력을 그대로 돌려준다.
# 주의: 집필할 때(2026-11-14, Claude Code 2.1.296) 문법과 옵션 이름만 확인하였고 실제로 실행하지 않았다.
#
# 환경 변수: REVIEW_BUDGET_USD(검토 한 번의 비용 상한, 달러. 기본 0.20)

PROMPT="${*: -1}"
exec claude -p "$PROMPT" \
  --agent reviewer \
  --permission-mode dontAsk \
  --permission-prompts none \
  --max-budget-usd "${REVIEW_BUDGET_USD:-0.20}"
