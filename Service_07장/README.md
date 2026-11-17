# 7장 실습 키트: 사용자 경험 설계 (사용자 여정과 정보 구조)

「LLM 서비스 개발」 7장(학사 9주차)의 실습 재료이다. 강의안 `Service_07장_학생용.md`의 0절에서 받는다.

## 받는 법

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Service_07장 ~/kits/
ls ~/kits/Service_07장
```

`~/kits-repo`는 1주차에 한 번 클론해 둔 수업용 키트 저장소이다(부록 A-12-2). 장마다 `git pull`로 새 키트를 받고, 이 장의 폴더를 저장소 밖의 `~/kits/`로 복사한 뒤, 이 장에서 필요한 파일만 개인 실습 저장소로 복사한다(강의안 0절, 부록 A-12-3). `cp -rn`은 이미 있는 파일을 덮어쓰지 않는다. `~/kits`가 없을 때 `mkdir -p` 없이 복사하면 `~/kits` 자체가 키트 폴더가 되므로 먼저 폴더를 만든다.

## 들어 있는 것과 쓰는 순서

| 순서 | 파일 | 쓰는 절 | 하는 일 |
|---|---|---|---|
| 0 | `기준산출물/` | 0절 | 6장의 명세서 v1이나 5장의 페르소나가 없을 때 복사해 쓴다 |
| 1 | `여정지도_양식.md` | 10절 | `jobprep/docs/설계/여정지도.md`로 복사해 채운다 |
| 2 | `카드목록.md` | 6절 [선택] | 카드 26장과 진행 순서, 지시문. 짝 활동(개방형 카드 소팅)에 쓴다 |
| 3 | `카드소팅기록_양식.md` | 6절 [선택] | 저장소의 `ch07/카드소팅/기록_짝.md`로 복사해 기록한다 |
| 4 | `견본/정보구조_견본.md` | 10절 | 사이트맵 골격. `jobprep/docs/설계/정보구조.md`로 복사해 고친다 |
| 5 | `견본/사용자흐름_견본.md` | 7절(따라 하기 1), 10절 | 흐름 표기 견본(FLOW-00)과 FLOW-01·02의 빈칸 |
| 6 | `견본/명세서v2_추가절_견본.md` | 8절, 10절 | 명세서에 붙일 「화면 목록」과 「사용자 흐름」 절 |
| 7 | `check_design.py` | 8절(따라 하기 2), 10절 | 화면 ID와 요구 ID의 연결, 여정 지도의 근거 표시를 검사한다 |
| 8 | `리뷰점검표_양식.md` | 9절, 10절 | 풀 리퀘스트를 리뷰할 때 쓴다 |
| - | `tests/` | 8절 [선택] | `check_design.py`의 테스트 |

## 연결 검사

```bash
cd ~/llm-service-lab
python ~/kits/Service_07장/check_design.py jobprep/docs
```

통과하면 마지막 줄이 `결과: 통과`이다. 오류가 있으면 `오류`로 시작하는 줄이 나오고 종료 코드가 1이다. 경고는 종료 코드를 바꾸지 않는다(`--strict`를 주면 경고도 실패로 친다). 출력은 UTF-8로 내보내므로 Windows의 Git Bash에서 `| grep`, `| tail`로 넘겨도 한글이 깨지지 않는다.

`check_design.py`는 파이썬 표준 라이브러리만 쓴다. 가상 환경을 켜지 않아도 `python`으로 실행된다(Windows의 Git Bash에는 `python3`이 없으므로 `python`으로 쓴다). 테스트를 돌릴 때만 pytest가 필요하다. 과목 공통의 가상 환경(부록 A-13)을 켠 터미널에서 실행한다.

```bash
source ~/llm-service-lab/.venv/Scripts/activate   # macOS는 .venv/bin/activate
cd ~/kits/Service_07장
python -m pip install -r requirements.txt
python -m pytest -q -p no:cacheprovider
```

마지막 줄이 `18 passed`이면 된다. `-p no:cacheprovider`는 키트 폴더에 `.pytest_cache`를 남기지 않게 한다. 테스트는 `교수/` 폴더를 읽지 않으므로 학생 키트와 교수 사본에서 결과가 같다. 저장소 맨 위의 `.gitignore`가 `.venv/`를 무시하는지 커밋 전에 확인한다.

## 기준 산출물

| 파일 | 내용 |
|---|---|
| `기준산출물/ch05/페르소나.md`, `문제정의.md`, `친화도.md` | 5장의 견본. 페르소나 PS-1 서지후, PS-2 임하람과 문제 정의 P-01~P-03. 5장 키트의 `교수/견본_*.md`를 복사한 것이며 가상 인물이다 |
| `기준산출물/ch05/기록/인터뷰_예시_01~04.md` | 5장의 수업용 예시 기록(가상). 견본의 인용 `[인터뷰_예시_01:L12]`가 이 기록의 줄 꼬리표를 가리킨다 |
| `기준산출물/jobprep/` | 6장의 견본. 명세서 v1.0(REQ-001~023, 공통 품질 요구 REQ-022·023), 추적표, `CLAUDE.md`. 6장 키트의 `교수/jobprep_예시/`를 복사한 것이다 |

자기 산출물이 있으면 자기 것을 쓴다. 없을 때만 복사한다.

```bash
cd ~/llm-service-lab
mkdir -p ch05/기록 jobprep/docs
cp -n ~/kits/Service_07장/기준산출물/ch05/*.md ch05/
cp -n ~/kits/Service_07장/기준산출물/ch05/기록/*.md ch05/기록/
cp -n ~/kits/Service_07장/기준산출물/jobprep/CLAUDE.md jobprep/
cp -n ~/kits/Service_07장/기준산출물/jobprep/docs/*.md jobprep/docs/
```

## mermaid 그림 확인

내 PC의 VS Code 1.121 이상은 마크다운 미리 보기(`Ctrl+Shift+V`)에서 mermaid 그림을 그린다. 그 아래 판이면 확장 「Markdown Preview Mermaid Support」를 설치하거나 Mermaid Live Editor(<https://mermaid.live>)에 블록 내용을 붙여 확인한다. GitHub는 풀 리퀘스트와 저장소의 마크다운에서 그림을 그린다.
