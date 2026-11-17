#!/usr/bin/env bash
# 하네스 조립 점검: 1~6장의 부품이 제자리에 있고, 설정 파일의 문법이 맞고, 훅이 견본 입력에 기대대로
# 반응하는지 본다. 모델을 부르지 않는다. 저장소 폴더(jobprep/)에서 실행한다.
#
# 사용: bash ops/harness/harness_check.sh
# 결과: 항목마다 [통과]/[실패]/[참고], 마지막 줄에 합계. 실패가 하나라도 있으면 종료 코드 1.
set -u
# JSON을 읽을 파이썬: 저장소의 가상 환경을 먼저 쓴다(부록 A-9-2: Scripts/python.exe 다음 bin/python).
if [ -x .venv/Scripts/python.exe ]; then PY3=.venv/Scripts/python.exe
elif [ -x .venv/bin/python ]; then PY3=.venv/bin/python
else PY3="$(command -v python || command -v python3)"; fi
pass=0; fail=0
ok()   { printf '  [통과] %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  [실패] %s\n' "$1"; fail=$((fail + 1)); }
note() { printf '  [참고] %s\n' "$1"; }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }

echo "1. 부품 파일 (괄호 안은 만든 장)"
check "CLAUDE.md (3장)" "[ -f CLAUDE.md ]"
check "경로별 규칙 .claude/rules/*.md (3장)" "ls .claude/rules/*.md"
check ".claude/settings.json (3·6장)" "[ -f .claude/settings.json ]"
check "테스트 동결 기록 tests/.baseline.json (2장)" "[ -f tests/.baseline.json ]"
check "스킬 incident-report (4장, 플러그인 또는 .claude/skills)" \
      "ls plugins/*/skills/incident-report/SKILL.md || ls .claude/skills/incident-report/SKILL.md"
check "마켓플레이스 .claude-plugin/marketplace.json (4장)" "[ -f .claude-plugin/marketplace.json ]"
check "MCP 설정 .mcp.json과 mcp/ops_server.py (5장)" "[ -f .mcp.json ] && [ -f mcp/ops_server.py ]"
check "훅 protect.sh, run_tests.sh, stop_gate.sh (6장)" \
      "[ -f .claude/hooks/protect.sh ] && [ -f .claude/hooks/run_tests.sh ] && [ -f .claude/hooks/stop_gate.sh ]"
check "검토 서브에이전트 .claude/agents/reviewer.md (6장)" "[ -f .claude/agents/reviewer.md ]"

echo "2. 설정 파일 문법(JSON)"
for f in .claude/settings.json .mcp.json .claude-plugin/marketplace.json plugins/*/.claude-plugin/plugin.json; do
  [ -f "$f" ] && check "$f" "'$PY3' -m json.tool '$f'"
done

echo "3. 설정의 내용"
check "deny에 Read(./.env)" "grep -q 'Read(./.env)' .claude/settings.json"
events="$("$PY3" -c 'import json; print(" ".join(sorted(json.load(open(".claude/settings.json", encoding="utf-8")).get("hooks", {}))))' 2>/dev/null)"
for e in PreToolUse PostToolUse Stop; do
  case " $events " in
    *" $e "*) ok "공유 설정에 $e 훅이 등록됨" ;;
    *) if [ "$e" = Stop ] && grep -q '"Stop"' .claude/settings.local.json 2>/dev/null; then
         bad "Stop 훅이 개인 설정(settings.local.json)에만 있음. 하네스로 공유하려면 settings.json으로 옮긴다(7장 4절)"
       else
         bad "공유 설정에 $e 훅이 없음"
       fi ;;
  esac
done
check ".gitignore에 settings.local.json" "grep -q 'settings.local.json' .gitignore"
check "requirements.txt에 mcp" "grep -q '^mcp==' requirements.txt"

echo "4. 지시 파일의 크기와 머리말"
lines=$(wc -l < CLAUDE.md 2>/dev/null | tr -d ' ')
check "CLAUDE.md ${lines:-0}줄 (200줄 이하)" "[ '${lines:-999}' -le 200 ]"
note "경로별 규칙 합계 $(cat .claude/rules/*.md 2>/dev/null | wc -l | tr -d ' ')줄"
for s in plugins/*/skills/*/SKILL.md .claude/skills/*/SKILL.md .claude/agents/*.md; do
  [ -f "$s" ] || continue
  check "$s 머리말(description)" "head -8 '$s' | grep -q '^description:'"
done

echo "5. 훅 단독 점검 (6장의 check_hooks.sh, 견본 입력 18개)"
if [ -f .claude/hooks/check_hooks.sh ]; then
  out="$(bash .claude/hooks/check_hooks.sh 2>&1)"
  summary="$(printf '%s\n' "$out" | tail -n 1)"
  if printf '%s\n' "$out" | grep -q 'FAIL'; then
    bad "check_hooks.sh: $summary"
    printf '%s\n' "$out" | grep 'FAIL' | sed 's/^/        /'
  else
    ok "check_hooks.sh: $summary"
  fi
fi

echo "6. 플러그인 검증 (claude가 있으면)"
if command -v claude >/dev/null 2>&1; then
  for p in plugins/*/; do
    [ -f "$p/.claude-plugin/plugin.json" ] || continue
    check "claude plugin validate $p" "claude plugin validate '$p'"
  done
  [ -f .claude-plugin/marketplace.json ] && check "claude plugin validate . (마켓플레이스)" "claude plugin validate ."
else
  note "claude 명령이 없어 건너뜀"
fi

echo
echo "결과: 통과 $pass, 실패 $fail"
[ "$fail" -eq 0 ]
