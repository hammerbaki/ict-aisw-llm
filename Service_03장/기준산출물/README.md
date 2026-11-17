# 기준 산출물: 2장의 개인 실습 저장소가 없을 때

3장은 2장에서 만든 개인 실습 저장소 `~/llm-service-lab`(GitHub 원격 포함)을 받아 쓴다. 이 저장소가 없으면 다음 순서로 최소 저장소를 만든 뒤 3장을 시작한다. 2장의 내용(커밋, 브랜치, 푸시)은 3장 안에서 다시 쓰이므로, 2장 교재를 함께 펴 둔다.

1. 최소 저장소를 만든다. 이미 있으면 아무것도 하지 않는다.

   ```bash
   bash ~/kits/Service_03장/기준산출물/make_lab.sh
   ```

2. GitHub에 비공개 저장소를 만들고 연결해 푸시한다. `gh auth status`로 로그인을 먼저 확인한다.

   ```bash
   cd ~/llm-service-lab
   gh repo create llm-service-lab --private --source . --remote origin --push
   git remote -v
   ```

3. `git status -sb`의 첫 줄이 `## main...origin/main`이면 준비가 끝났다.

`make_lab.sh`는 `README.md`, `.gitignore`, 빈 `ch03/` 폴더만 만든다. 2장의 `CLAUDE.md`와 `ch02/` 실습 파일은 들어 있지 않다.
