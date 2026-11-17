# 기준산출물: 1장을 마치지 못한 학습자용

2장은 1장의 결과(개인 저장소 `~/agent-lab/jobprep`과 운영 문서 두 편) 위에서 진행한다. 1장을 마친 학습자는 이 폴더를 쓰지 않는다. 명령은 내 PC의 Git Bash(macOS는 터미널)에서 친다.

## 1. 저장소가 없을 때

1장의 키트에서 기준 저장소를 복사해 git 저장소로 만든다(부록 A-8-1). 원격(GitHub) 연결은 1장과 부록 A-8-2를 따라 나중에 해도 된다.

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits ~/agent-lab
cp -rn ~/kits-repo/Agent_01장 ~/kits/
cp -rn ~/kits/Agent_01장/jobprep ~/agent-lab/
cd ~/agent-lab/jobprep
git init -b main
git add .
git commit -m "chore: 기준 저장소 jobprep을 받음"
python -m venv .venv                 # macOS: python3 -m venv .venv
source .venv/Scripts/activate        # macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

마지막 줄이 `43 passed`이면 된다.

## 2. 운영 문서가 없을 때

`docs/운영/운영요건.md`와 `docs/운영/역할정의.md`는 1장의 산출물이다. 없으면 이 폴더의 견본을 넣는다. 견본은 2장이 쓰는 부분(신뢰성과 재현성의 요건, 구현 역할의 완료 조건)만 담은 줄인 판이다.

```bash
cd ~/agent-lab/jobprep
cp -n ~/kits/Agent_02장/기준산출물/docs/운영/*.md docs/운영/
git add docs/운영/
git commit -m "docs: 1장 운영 문서의 기준산출물을 넣음"
```
