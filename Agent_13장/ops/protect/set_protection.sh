#!/usr/bin/env bash
# main 브랜치(와 에이전트·루프 브랜치)의 보호 규칙을 gh api로 설정하고 확인한다 (13장 6-3).
#
# 이 스크립트는 교재 집필 때 실제 GitHub 저장소에 실행해 보지 못하였다(2026-11-14).
# 요청 본문의 형식은 GitHub REST API 문서(Repository rules, Branch protection)와 대조하였다.
# 화면(Settings → Rules → Rulesets)에서 같은 설정을 할 수 있으며, 교재 6절은 화면 설정을 기본으로 한다.
#
# 쓰는 법 (저장소 폴더에서, 저장소 관리자 권한이 있는 gh 로그인 상태로)
#   bash ops/protect/set_protection.sh ruleset     규칙 집합(ruleset)을 만든다 (권장)
#   bash ops/protect/set_protection.sh agent       agent/*(10장), loop/*(8장) 브랜치에 강제 푸시 금지를 건다
#   bash ops/protect/set_protection.sh classic     예전 방식의 보호 브랜치 규칙을 만든다
#   bash ops/protect/set_protection.sh show        지금 걸린 규칙을 본다
# {owner}/{repo}는 gh가 이 저장소의 원격에서 채운다.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
case "${1:-show}" in
  ruleset)
    gh api --method POST "repos/{owner}/{repo}/rulesets" --input "$HERE/ruleset.json" \
      --jq '"만든 규칙 집합: id=\(.id) 이름=\(.name) 상태=\(.enforcement)"'
    ;;
  agent)
    gh api --method POST "repos/{owner}/{repo}/rulesets" --input "$HERE/ruleset_agent.json" \
      --jq '"만든 규칙 집합: id=\(.id) 이름=\(.name) 상태=\(.enforcement)"'
    ;;
  classic)
    gh api --method PUT "repos/{owner}/{repo}/branches/main/protection" --input "$HERE/branch_protection.json" \
      --jq '"필수 검사: \(.required_status_checks.contexts | join(", "))"'
    ;;
  show)
    echo "== 이 브랜치에 적용되는 규칙(규칙 집합)"
    gh api "repos/{owner}/{repo}/rules/branches/main" --jq '.[] | .type'
    echo "== 예전 방식의 보호 규칙"
    if classic="$(gh api "repos/{owner}/{repo}/branches/main/protection" \
         --jq '.required_status_checks.contexts' 2>/dev/null)"; then
      echo "$classic"
    else
      echo "(없음)"
    fi
    ;;
  *)
    echo "쓰는 법: bash ops/protect/set_protection.sh [ruleset|agent|classic|show]" >&2
    exit 2
    ;;
esac
