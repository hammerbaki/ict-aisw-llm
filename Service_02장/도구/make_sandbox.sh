#!/usr/bin/env bash
# 되돌리기와 브랜치를 연습할 연습용 저장소 ~/git-sandbox 를 만든다.
# 개인 실습 저장소(llm-service-lab)와 따로 두어, 위험한 명령을 실험해도 실습 기록이 다치지 않게 한다.
# 사용법: bash ~/kits/Service_02장/도구/make_sandbox.sh  [만들 위치, 기본 ~/git-sandbox]
set -euo pipefail

DIR="${1:-$HOME/git-sandbox}"
if [ -e "$DIR" ]; then
  echo "이미 있다: $DIR"
  echo "다시 만들려면 먼저 지운다: rm -rf \"$DIR\""
  exit 1
fi

if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
  echo "git 사용자 정보가 없다. 2절의 git config --global user.name / user.email 을 먼저 한다."
  exit 1
fi

git init -q -b main "$DIR"
cd "$DIR"

printf '# 면접 준비 메모\n\n- 자기소개 1분\n' > notes.md
git add notes.md
git commit -q -m "면접 준비 메모 시작"

printf -- '- 지원 동기\n' >> notes.md
git commit -q -am "지원 동기 항목 추가"

printf -- '- 프로젝트 경험\n' >> notes.md
git commit -q -am "프로젝트 경험 항목 추가"

echo "만들었다: $DIR"
git log --oneline
