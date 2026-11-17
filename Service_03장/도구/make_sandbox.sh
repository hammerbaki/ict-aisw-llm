#!/usr/bin/env bash
# 3장 연습 저장소를 만든다: 로컬 원격 저장소(bare) 하나와 두 사람의 클론 둘.
# GitHub 없이 푸시, 받아오기, 병합 충돌, 병합 방식을 연습하는 데 쓴다.
# 혼자 남은 학생의 대안 절차에도 쓴다.
#
# 사용법: bash make_sandbox.sh [만들 폴더]      (기본값: ~/ch03-sandbox)
#   만들어지는 것
#     <폴더>/origin.git   원격 역할을 하는 bare 저장소 (GitHub 저장소 대신)
#     <폴더>/a            개발자A의 클론
#     <폴더>/b            개발자B의 클론
set -euo pipefail

KIT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$HOME/ch03-sandbox}"

if [ -e "$DEST" ]; then
  echo "이미 있다: $DEST"
  echo "다시 만들려면 먼저 지운다: rm -rf \"$DEST\""
  exit 1
fi

mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"   # 상대 경로로 받아도 절대 경로로 바꾼다
git init -q --bare -b main "$DEST/origin.git"

# 첫 커밋은 「교수」가 키트의 시작 파일로 만든다
SEED="$(mktemp -d)"
cp -r "$KIT/team-lab/." "$SEED/"
git -C "$SEED" init -q -b main
git -C "$SEED" -c core.autocrlf=false add .   # Windows의 LF→CRLF 경고를 내지 않게 한다
git -C "$SEED" -c user.name="교수" -c user.email="prof@example.com" \
    commit -q -m "팀 실습 저장소의 시작 파일"
git -C "$SEED" push -q "$DEST/origin.git" main
rm -rf "$SEED"

for who in a b; do
  git clone -q "$DEST/origin.git" "$DEST/$who"
  name="개발자$(echo "$who" | tr 'ab' 'AB')"
  git -C "$DEST/$who" config user.name "$name"
  git -C "$DEST/$who" config user.email "$who@example.com"
  git -C "$DEST/$who" config core.quotePath false   # 한글 파일 이름을 그대로 보인다
done

echo "연습 저장소를 만들었다: $DEST"
echo "  원격   $DEST/origin.git"
echo "  개발자A $DEST/a"
echo "  개발자B $DEST/b"
git -C "$DEST/a" log --oneline
