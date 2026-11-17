#!/usr/bin/env bash
# 판 태그 하나의 커밋에서 CI의 네 검사가 모두 성공했는지 GitHub에 묻는다 (「AI에이전트 기획 및 개발」 13장).
# 「CI를 통과한 판만 배포한다」를 사람의 기억이 아니라 이 스크립트가 지킨다.
# pages.yml이 배포 전에 부르고, 내 PC에서 태그를 붙인 뒤 손으로 불러 볼 수도 있다.
#
# 쓰는 법 (저장소 폴더에서, gh 로그인 상태로. 태그는 원격에 푸시되어 있어야 한다)
#   bash ops/release/ci_passed.sh v1.0.0
# 환경 변수
#   GH_REPO          소유자/저장소. 없으면 gh가 이 폴더의 원격에서 채운다({owner}/{repo})
#   REQUIRED_CHECKS  기다리는 검사의 이름(기본 "test eval secrets rules". ci.yml의 작업 이름과 같아야 한다)
# 종료 코드: 0 모두 success, 1 하나라도 success가 아님(없음 포함), 2 사용 오류
set -euo pipefail

TAG="${1:-}"
REQUIRED_CHECKS="${REQUIRED_CHECKS:-test eval secrets rules}"
if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "[ci_passed] 판 태그의 형식이 아니다(vX.Y.Z): ${TAG:-(없음)}" >&2
  exit 2
fi
if [[ -n "${GH_REPO:-}" ]]; then R="repos/$GH_REPO"; else R="repos/{owner}/{repo}"; fi

SHA="$(gh api "$R/commits/$TAG" --jq .sha 2>/dev/null || true)"
if [[ ! "$SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "[ci_passed] 원격에서 태그를 찾지 못했다: $TAG (git push origin $TAG 를 했는가)" >&2
  exit 1
fi
echo "[ci_passed] 판 $TAG = 커밋 ${SHA:0:7}"

failed=0
for check in $REQUIRED_CHECKS; do
  # 같은 검사를 다시 돌렸으면 가장 나중에 끝난 결과를 본다
  conclusion="$(gh api "$R/commits/$SHA/check-runs?per_page=100" \
    --jq "[.check_runs[] | select(.name == \"$check\")] | sort_by(.completed_at) | last | .conclusion // empty" \
    2>/dev/null || true)"
  echo "[ci_passed] 검사 $check: ${conclusion:-없음}"
  [[ "$conclusion" == "success" ]] || failed=1
done

if (( failed )); then
  echo "[ci_passed] 중단: CI를 통과하지 않은 판이다. 배포하지 않는다" >&2
  exit 1
fi
echo "[ci_passed] 검사 $(wc -w <<< "$REQUIRED_CHECKS")개가 모두 success이다"
