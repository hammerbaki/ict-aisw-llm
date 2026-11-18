# 11장 키트: 애플리케이션의 분석과 UI 설계

「LLM 서비스 개발」 11장(학사 13주차)의 실습 재료이다. 강의안은 `Service_11장_학생용.md`이다. 서비스 5(오픈소스 데스크톱 앱의 기능 하나)의 앞 절반으로, 대상 앱 FromScratch의 자동 저장 기능을 분석해 기능 명세, 화면 명세, HTML 프로토타입을 만든다. 12장이 이 산출물로 두 구현을 만든다.

## 받는 법

```bash
git -C ~/kits-repo pull && cp -rn ~/kits-repo/Service_11장 ~/kits/
source ~/llm-service-lab/.venv/Scripts/activate      # macOS: source ~/llm-service-lab/.venv/bin/activate
cd ~/kits/Service_11장
python -m pip install -r requirements.txt
python -m pytest -q                                  # 34 passed (교수/가 없는 학생 키트는 32 passed, 2 skipped)
```

키트는 저장소 밖(`~/kits/`)에 두고 고치지 않는다. 양식은 `~/llm-service-lab/ch11/`로 복사해 쓴다. 대상 앱의 저장소도 개인 실습 저장소 밖(`~/target-app`)에 둔다.

## 들어 있는 것

| 경로 | 쓰는 절 | 내용 |
|---|---|---|
| `관찰기록_양식.md` | 1-3 | 앱을 실행해 본 것과 「보고도 알 수 없는 것」 |
| `기능명세_양식.md` | 1-5 | 경로, EARS 요구와 근거의 종류(확인, 추측, 정함), 매체 차이 |
| `화면명세_양식.md` | 4절, 5-2 | 화면 하나의 일곱 칸, 프로토타입 대조 기록, 키보드 점검 기록 |
| `디자인토큰_견본.md` | 3-2, 5-3 | 메모장 웹 재구현의 색과 크기. FromScratch의 바탕색, 글자색, 저장 안내 색을 옮겼다. **대비 미달 한 쌍(저장 상태 문구, 3.18:1)이 원본에서 그대로 들어 있다** |
| `예제/메모_나쁜예.html` | 3-4 | 접근성 문제를 일부러 넣은 메모 화면. 점검기가 찾는 것(오류 8, 경고 2)과 찾지 못하는 것(초점 표시, 대비)이 함께 있다 |
| `예제/메모_고친예.html` | 3-4 | 위를 고친 판. 점검기 오류 0건 |
| `tools/contrast.py` | 3-2, 5-4 | 대비 계산기. 디자인토큰 파일의 「대비 쌍」 표 또는 `--pair` 두 색을 WCAG 2.2 공식으로 판정한다 |
| `tools/tokens_to_css.py` | 5-3 | 디자인토큰 파일 → `tokens.css`(CSS 사용자 지정 속성) |
| `tools/html_check.py` | 3-4, 5-4 | HTML 기본 점검기(lang, title, img의 alt, 입력의 레이블, 단추와 링크의 이름, 중복 id, tabindex, div 클릭) |
| `tools/keyboard_walk.py` | 3-4, 5-4 [선택] | Tab 키로 초점이 가는 순서, 초점 표시, 24px 미만을 기록한다. Playwright와 브라우저가 필요하다 |
| `tools/tokenfile.py` | | 위 도구들이 함께 쓰는 디자인토큰 파일 읽기 모듈 |
| `tests/` | 0절 | 도구의 테스트 |
| `교수/` | 교수용 | 정답 예시(기능 명세, 화면 명세, 디자인토큰 v0.2, 프로토타입). 학생 키트 저장소에 넣지 않는다 |

## 쓰는 순서

```bash
KIT=~/kits/Service_11장
mkdir -p ~/llm-service-lab/ch11 && cd ~/llm-service-lab/ch11
cp -n "$KIT"/관찰기록_양식.md 관찰기록.md
cp -n "$KIT"/기능명세_양식.md 기능명세.md
cp -n "$KIT"/화면명세_양식.md 화면명세.md
cp -n "$KIT"/디자인토큰_견본.md 디자인토큰.md

python "$KIT/tools/contrast.py" 디자인토큰.md                 # 미달 1건, 종료 코드 1 (5-3에서 고친다)
mkdir -p prototype
python "$KIT/tools/tokens_to_css.py" 디자인토큰.md -o prototype/tokens.css
python "$KIT/tools/html_check.py" prototype/
python "$KIT/tools/keyboard_walk.py" prototype/index.html --channel msedge   # 선택
```

`keyboard_walk.py`는 Windows의 Edge(`--channel msedge`)나 Chrome(`--channel chrome`)이 있으면 브라우저를 따로 받지 않는다. 둘 다 없으면 `python -m playwright install --only-shell chromium`이 필요하다(부록 A-18). 이 도구가 없어도 사람이 Tab 키로 하는 점검으로 실습을 끝낼 수 있다.

## 확인한 환경

2026-11-18, Windows 11(빌드 26300)의 Git Bash, Python 3.13.7 가상 환경(pytest 9.2.0, playwright 1.64.0), Microsoft Edge 157에서 `python -m pytest -q`(34 passed), 위 「쓰는 순서」의 도구 명령, `keyboard_walk.py --channel msedge`를 실행하였다. 대상 앱(FromScratch)의 설치와 실행, REA, Claude Code의 단계는 실행하지 않았다(교수 리허설). macOS에서는 실행하지 않았다.
