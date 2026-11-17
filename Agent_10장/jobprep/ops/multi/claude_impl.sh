#!/usr/bin/env bash
# ops/multi/claude_impl.sh: 실제 Claude Code(헤드리스)로 구현 에이전트 하나를 실행하는 감싸개.
# dispatch.sh가 작업 공간 안에서 부르고, 마지막 인자로 지시문을 넘긴다.
#
#   AGENT_CMD="bash ops/multi/claude_impl.sh" bash ops/multi/run_issue.sh ISSUE-07 T1 T2
#
# 감싸개를 따로 두는 까닭: --allowedTools의 규칙에는 빈칸이 들어가므로(Bash(python -m pytest *))
# AGENT_CMD 문자열 하나에 담으면 셸이 빈칸에서 잘라 버린다.
# 주의: 집필할 때(2026-11-14, Claude Code 2.1.296) 이 파일은 문법(bash -n)과 옵션 이름(claude --help)만
# 확인하였고, 실제 모델을 불러 실행하지는 않았다. 수업 전에 교수가 한 번 실행해 본다.
#
# 허용 규칙의 python은 가상 환경을 켠 셸의 python이다. 가상 환경을 켠 터미널에서 run_issue.sh를 실행한다
# (.venv/bin/python 같은 경로 호출은 Windows에 없으므로 규칙에 넣지 않는다. 부록 A-9).
#
# 환경 변수: AGENT_BUDGET_USD(시도 한 번의 비용 상한, 달러. 기본 0.50)

PROMPT="${*: -1}"
exec claude -p "$PROMPT" \
  --agent implementer \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "Bash(python -m pytest *),Bash(pytest *),Bash(git add *),Bash(git commit *),Bash(git status *),Bash(git diff *)" \
  --disallowedTools "Bash(git push *),Bash(git merge *),Bash(git rebase *),Bash(git reset *),Bash(git switch *),Bash(git checkout *)" \
  --max-budget-usd "${AGENT_BUDGET_USD:-0.50}" \
  --output-format json
