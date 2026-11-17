#!/usr/bin/env bash
# 2장의 개인 실습 저장소(llm-service-lab)가 없는 학생을 위한 최소 저장소를 만든다.
# 이미 저장소가 있으면 아무것도 하지 않는다. GitHub 원격 연결은 README의 명령으로 따로 한다.
#
# 사용법: bash make_lab.sh [만들 폴더]     (기본값: ~/llm-service-lab)
set -euo pipefail

DEST="${1:-$HOME/llm-service-lab}"
if [ -d "$DEST/.git" ]; then
  echo "이미 저장소가 있다: $DEST"
  git -C "$DEST" log --oneline -3
  exit 0
fi

mkdir -p "$DEST/ch03"
cat > "$DEST/README.md" <<'MD'
# llm-service-lab

「LLM 서비스 개발」 개인 실습 저장소. 장마다 `chNN/` 폴더에 산출물을 둔다.
2장의 저장소가 없어 3장의 기준 산출물(`make_lab.sh`)로 만들었다.
MD
cat > "$DEST/.gitignore" <<'IGN'
.env
.venv/
__pycache__/
.DS_Store
IGN
git -C "$DEST" init -q -b main
git -C "$DEST" add README.md .gitignore
git -C "$DEST" commit -q -m "개인 실습 저장소의 최소 구성 (3장 기준 산출물)"
echo "만들었다: $DEST"
git -C "$DEST" log --oneline
