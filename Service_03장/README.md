# Service_03장 키트: 팀 공동 작업 (GitHub 기반 협업 흐름)

「LLM 서비스 개발」 3장(학사 4주차)의 실습 재료다. 강의안은 `Service_03장_학생용.md`이다.

## 받는 법

내 PC의 터미널(Windows는 Git Bash, macOS는 기본 터미널)에서 실행한다. 키트 저장소 `~/kits-repo`는 1주차에 클론해 두었다(부록 A-12).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Service_03장 ~/kits/
ls ~/kits/Service_03장
```

## 들어 있는 것

| 경로 | 쓰임 | 강의안의 절 |
|---|---|---|
| `team-lab/` | 팀 실습 저장소 `<팀>-lab`의 시작 파일. 교수가 이 폴더로 팀마다 저장소를 미리 만들어 둔다. 13장 9-5에서 사용성 문제의 이슈를 올릴 때 다시 쓴다 | 0-3, 7 |
| `team-lab/서비스소개.md` | 충돌 실습 파일. 「한 줄 소개」 줄은 짝 1(A·B), 「핵심 기능」 줄은 짝 2(C·D)가 고친다. 연습 저장소(6-2)도 이 파일로 충돌을 만든다 | 6-2~6-4, 7-3, 7-4 |
| `team-lab/members/_양식.md` | 팀원 소개 파일의 양식 | 7-2 |
| `team-lab/.github/ISSUE_TEMPLATE/` | 이슈 양식(`task.md`)과 양식 선택 화면 설정(`config.yml`). 설명은 부록 B-6의 「이슈 템플릿과 이슈 폼」 | 3, 7-2 |
| `team-lab/.github/pull_request_template.md` | 풀 리퀘스트 설명 양식 | 4-3, 7-2, 7-3 |
| `project-repo/README_양식.md` | 프로젝트실습Ⅰ 팀 저장소의 README 양식. 그 과목의 첫 주에 쓴다 | 0-1 |
| `협업기록_양식.md` | 개인 저장소의 `ch03/협업기록.md`로 복사해 채우는 양식 | 4-4, 7-5 |
| `리뷰점검표.md` | 리뷰어가 쓰는 점검표. 기준은 부록 B-6의 「좋은 리뷰의 기준」 | 7-2, 7-4 |
| `도구/make_sandbox.sh` | GitHub 없이 연습하는 로컬 원격(bare) 하나와 클론 둘을 내 PC에 만든다(기본 `~/ch03-sandbox`). 4-1의 그래프와 부록 B-6의 「읽기: 푸시 거부」의 출력도 이것으로 얻었다 | 6-2 |
| `도구/labels.sh`, `labels_lab.tsv`, `labels_project.tsv` | 라벨을 한꺼번에 만든다(`gh label create --force`). `labels_lab.tsv`는 팀 실습 저장소의 라벨 일곱 개(13장 이슈 템플릿의 `usability` 포함), `labels_project.tsv`는 프로젝트실습Ⅰ 저장소의 라벨이다. 교수가 저장소를 준비할 때 쓴다. 설명은 부록 B-6의 「라벨과 마일스톤」 | 4-4 |
| `도구/check_ch03.py` | 완료 기준 점검(병합된 PR, 충돌 해결 커밋, 충돌 표시, 협업기록). 표준 라이브러리만 쓴다 | 6-4, 7-5 |
| `도구/tests/` | `check_ch03.py`의 테스트 | |
| `기준산출물/` | 2장의 개인 저장소가 없는 학생이 최소 저장소를 만드는 스크립트와 안내 | 0-2 |
| `교수/` | 진행 지시, 저장소 준비 스크립트와 보호 규칙(JSON), 시연 스크립트, 판정 예시. 학생용 키트 저장소와 공개 사이트에 넣지 않는다 | |

## 쓰는 순서

1. 0절: 키트를 받고 `gh auth status`, `git config --global core.quotePath false`를 확인한다. 팀 실습 저장소를 `~/teams/<팀>-lab`에 클론하고, 초안 파일을 둘 `~/ch03-drafts/`를 만든다.
2. 4-4절(따라 하기): 개인 저장소에서 이슈 → 브랜치 → 초안 PR → 병합을 한 바퀴 돈다. 이때 `협업기록_양식.md`를 `ch03/협업기록.md`로 복사해 함께 병합한다.
3. 6-2~6-4절(따라 하기): `bash ~/kits/Service_03장/도구/make_sandbox.sh`로 연습 저장소를 만들어 충돌을 재현하고 해결한 뒤 `check_ch03.py --lab ~/ch03-sandbox/a`로 점검한다.
4. 7절(핵심 실습): 팀 실습 저장소에서 이슈 → PR → 리뷰 → 병합과 충돌 해결을 한다. 팀원 소개는 `members/<아이디>.md`에 둔다.
5. 7-5절: `ch03/협업기록.md`를 채우고(5절에는 6절 연습 저장소의 그래프) `python ~/kits/Service_03장/도구/check_ch03.py`로 점검한 뒤 개인 저장소에 커밋한다.
6. 혼자 남았을 때의 절차는 부록 B-6의 「대안 절차: 단독 수행」을 따른다.

## 테스트

가상 환경은 개인 실습 저장소의 `~/llm-service-lab/.venv` 하나를 쓴다(부록 A-13). 키트 폴더에 가상 환경을 따로 만들지 않는다. 터미널에서 가상 환경을 켠 뒤 `python`으로 부른다(macOS는 `.venv/bin/activate`).

```bash
source ~/llm-service-lab/.venv/Scripts/activate
python -m pip install -r ~/kits/Service_03장/도구/requirements.txt
cd ~/kits/Service_03장/도구
python -m pytest -q
```

8개가 통과한다(2026-11-16, 2026-11-18에 다시 실행. Windows 11 Git Bash, Python 3.13.7, pytest 9.2.0, 약 1분 20초. git 프로세스를 많이 띄우므로 Windows에서 느리다). `check_ch03.py`의 충돌 판정은 git 2.38 이상에서 `git merge-tree --write-tree`를 쓰고, 그보다 낮은 git에서는 예전 형식의 `git merge-tree`로 판정한다.
