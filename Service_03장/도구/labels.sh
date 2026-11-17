#!/usr/bin/env bash
# 라벨 목록 파일(TSV)대로 GitHub 저장소에 라벨을 만든다. 같은 이름이 있으면 색과 설명을 고친다.
#
# 사용법: bash labels.sh <라벨 파일> <소유자/저장소>
#   예:   bash labels.sh labels_lab.tsv "$OWNER/$REPO"
#         DRY_RUN=1 bash labels.sh labels_project.tsv "$OWNER/$PROJ"   (실행하지 않고 명령만 보인다)
# 필요한 것: gh 로그인(gh auth status), 저장소의 write 이상 권한
set -euo pipefail

if [ $# -ne 2 ]; then
  sed -n '2,7p' "$0"
  exit 1
fi
FILE="$1"
REPO="$2"

while IFS=$'\t' read -r name color desc; do
  desc="${desc%$'\r'}"   # Windows에서 CRLF로 받은 파일이면 줄 끝의 CR을 지운다
  case "$name" in ''|'#'*) continue ;; esac
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "gh label create \"$name\" --color $color --description \"$desc\" --force -R $REPO"
  else
    gh label create "$name" --color "$color" --description "$desc" --force -R "$REPO"
  fi
done < "$FILE"
