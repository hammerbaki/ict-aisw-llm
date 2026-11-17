# Service_09장 키트: 웹 프로덕트의 구현과 배포

「LLM 서비스 개발」 9장(학사 11주차)의 실습 재료다. 명세서와 화면 명세에서 공고 모아보기·관심 공고·지원 일정 관리 웹(`jobprep/web/`)을 구현하고, 인수 조건으로 검사하고, GitHub Pages에 배포한 뒤, 명세 변경 한 건을 반영해 다시 배포한다.

## 들어 있는 것

| 경로 | 내용 | 어디로 가는가 (`~/llm-service-lab/` 기준) |
|---|---|---|
| `README.md` | 이 안내 | |
| `작업목록_양식.md` | 계획을 작업 목록으로 옮기는 양식 | `jobprep/docs/작업목록.md` |
| `인수조건_양식.md` | 인수 조건 표(Given-When-Then)의 양식 | `jobprep/docs/인수조건.md` |
| `배포기록_양식.md` | 배포 주소와 배포 이력의 양식 | `jobprep/docs/배포기록.md` |
| `화면명세_검사용식별자.md` | 화면 명세에 붙이는 「검사용 약속」 절 | `jobprep/docs/설계/화면명세.md`의 맨 뒤 |
| `변경요청_CR-01.md` | 핵심 실습 8단계의 명세 변경 요청(관심 공고의 마감순 정렬, REQ-040, `spec-v4`) | 읽기만 한다 |
| `CLAUDE_웹구현규칙.md` | `jobprep/CLAUDE.md`에 더하는 「웹 구현 규칙」 절 | `jobprep/CLAUDE.md`의 맨 뒤 |
| `시작/` | 공고 자료 30건(`data/jobs.json`), 디자인 토큰 CSS(8장 토큰 + 9장 구현의 별칭), 자동 검사(`check/`) | `jobprep/web/` |
| `도구/predeploy.py` | 배포 전 점검과 공개 폴더(`_site`) 만들기 | `jobprep/tools/predeploy.py` |
| `배포/.github/workflows/pages.yml` | GitHub Pages 배포 워크플로 견본 | `.github/workflows/pages.yml` (저장소 맨 위) |
| `배포/gitignore_추가.txt` | `.gitignore`에 더할 줄 | `.gitignore` |
| `기준산출물/jobprep/` | 8장 정답(`Service_08장/교수/정답/`)과 7장 정본을 복사한 견본: 명세서 v3(REQ-001~039)과 추적표, 설계 문서(화면 명세 v3 SCR-01~04, 디자인 토큰, 접근성 점검, 정보 구조, 사용자 흐름, 여정 지도), 프로토타입(index, job, schedule, schedule-new), CLAUDE.md | 앞 장 산출물이 없을 때만 `jobprep/` |
| `교수/` | 정답과 시연 재료. 학생용 키트 저장소에는 들어 있지 않다 | |

## 쓰는 순서

1. 0절: 키트를 `~/kits/`에 받고, 앞 장 산출물을 확인한다. 없으면 `기준산출물/`을 복사한다(`cp -rn`이라 있는 파일은 덮어쓰지 않는다). 시작 파일, 도구, 워크플로, `.gitignore`의 줄, 화면 명세의 「검사용 약속」, `CLAUDE.md`의 「웹 구현 규칙」을 넣고 한 커밋으로 남긴다.
2. 6절(따라 하기 1): Playwright를 준비하고(부록 A-18), 구현 전의 정적 검사가 실패하는 것을 본다.
3. 7절(따라 하기 2): 저장소의 Settings → Pages에서 Source를 GitHub Actions로 바꾸고 `배포기록_양식.md`를 복사해 「배포 설정」을 적는다.
4. 9절(핵심 실습): 계획과 작업 목록(`작업목록_양식.md`), 인수 조건 표(`인수조건_양식.md`), 작업 단위의 구현과 검사, 전체 검사와 손 점검, Aside 점검(로컬 `http://localhost:8100/`), 첫 배포(`도구/predeploy.py`, `pages.yml`), 에이전트 판정의 대조, 변경 요청(`변경요청_CR-01.md`, REQ-040, `spec-v4`)과 재배포의 순서로 한 흐름이다.

## 받는 명령

가상 환경(`~/llm-service-lab/.venv`)을 켠 터미널에서 실행한다(부록 A-13). 키트 저장소의 클론은 부록 A-12-2에 있다.

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits && cp -rn ~/kits-repo/Service_09장 ~/kits/
KIT=~/kits/Service_09장
cd ~/llm-service-lab
mkdir -p jobprep/web jobprep/tools jobprep/docs
cp -rn "$KIT/시작/." jobprep/web/
cp -n  "$KIT/도구/predeploy.py" jobprep/tools/
cp -rn "$KIT/배포/.github" .
cat "$KIT/배포/gitignore_추가.txt" >> .gitignore
cat "$KIT/화면명세_검사용식별자.md" >> jobprep/docs/설계/화면명세.md
cat "$KIT/CLAUDE_웹구현규칙.md" >> jobprep/CLAUDE.md
python -m pip install -r jobprep/web/check/requirements.txt
python -m playwright install --only-shell chromium
```

키트는 저장소 밖(`~/kits/`)에 두고 필요한 파일만 저장소로 옮긴다. 가상 환경은 과목 공통의 `~/llm-service-lab/.venv` 하나를 쓴다(부록 A-13). 로컬 웹 서버는 포트 8100(`python -m http.server 8100 --bind 127.0.0.1`, 부록 A-16)으로 띄운다. 브라우저 검사(`check_browser.py`)는 스스로 빈 포트에 서버를 띄우므로 8100과 겹치지 않는다.

## 확인한 환경

- 2026-11-17(결정 11 개편): Windows 11(빌드 26300), Git Bash, Python 3.13.7. 키트 저장소 흐름(`~/kits-repo` 클론, `cp -rn`)과 0절의 명령, `check_static.py`(구현 전 6/1, 견본 8/8), `check_browser.py`(Playwright 1.64.0, chromium_headless_shell-1248; `교수/web_v1` 20/20, `교수/web` 22/22, `web_v1`에 AC-040 두 개 0/2), `python -m http.server 8100 --bind 127.0.0.1`, `predeploy.py`, `git check-ignore`, CR-01 한 커밋. 교수용 강의안의 「확인한 것」에 출력이 있다.
- 2026-11-14(집필): 같은 PC에서 위 검사와 로컬 bare 저장소를 쓴 git 흐름.
- GitHub에서의 실제 워크플로 실행, Pages 설정 화면, Aside의 실행, macOS에서의 실행은 확인하지 못하였다. 교수용 강의안의 「확인한 것과 확인하지 못한 것」을 본다.
