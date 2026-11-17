# 8장 키트: UI 설계와 프로토타이핑

「LLM 서비스 개발」 8장(학사 10주차)의 실습 재료다. 강의안 `Service_08장_학생용.md`의 0절과 10절이 이 키트를 쓰는 순서를 정한다.

## 들어 있는 것

| 경로 | 무엇 | 쓰는 절 |
|---|---|---|
| `화면명세_양식.md` | 화면 명세 양식. 복사해 `jobprep/docs/설계/화면명세.md`로 쓴다 | 8절, 10절 |
| `디자인토큰_견본.md` | 디자인 토큰 견본 v0.1. 복사해 `jobprep/docs/설계/디자인토큰.md`로 쓴다. **대비 미달 한 쌍이 일부러 들어 있다** | 3절, 6절, 10절 |
| `접근성점검_양식.md` | 접근성 점검표. 복사해 `jobprep/docs/설계/접근성점검.md`로 쓴다 | 6절, 10절 |
| `prototype_시작/` | 프로토타입 시작 파일(머리, 내비게이션, 토큰, 기본 스타일, 가짜 데이터). 복사해 `jobprep/prototype/`으로 쓴다 | 9절, 10절 |
| `tools/contrast.py` | 대비 계산기. 디자인토큰.md의 「대비 쌍」 표를 WCAG 2.2 공식으로 판정한다 | 6절 |
| `tools/tokens_to_css.py` | 디자인토큰.md → `tokens.css`(CSS 사용자 지정 속성) 변환기 | 3절 |
| `tools/html_check.py` | HTML 기본 점검기(lang, title, img의 alt, 입력의 레이블, 버튼과 링크의 이름, 중복 id, tabindex, div 클릭) | 6절 |
| `tools/keyboard_walk.py` | 키보드 이동 기록기(선택, Playwright 필요) | 9절 |
| `tools/tokenfile.py` | 위 도구들이 함께 쓰는 디자인토큰.md 읽기 모듈 | |
| `예제/위계_비교.html` | 시각적 위계가 없는 목록과 있는 목록의 비교, 흐림 검사 단추 | 2절 |
| `예제/일정등록_나쁜예.html` | 접근성 문제를 일부러 넣은 양식. 점검기가 찾는 것과 못 찾는 것을 비교한다 | 5절, 6절 |
| `기준산출물/docs/` | 7장 정답 예시의 사본(명세서 v2.0, 추적표, 정보구조, 사용자흐름, 여정지도). 7장 결과가 없는 학습자만 쓴다 | 0절 |
| `tests/` | 도구의 테스트 | 0절 |
| `requirements.txt` | pytest 9.2.0, playwright 1.64.0 판 고정 | 0절 |

## 쓰는 순서

명령은 내 PC의 터미널(Windows는 Git Bash, macOS는 기본 터미널)에서 실행한다. 강의안의 꼬리표는 `[터미널]`이다.

```bash
# 키트 받기(부록 A-12-3). 키트는 저장소 밖(~/kits)에 둔다
git -C ~/kits-repo pull
mkdir -p ~/kits && cp -rn ~/kits-repo/Service_08장 ~/kits/
KIT=~/kits/Service_08장

# 가상 환경을 켠다(부록 A-13. macOS는 ~/llm-service-lab/.venv/bin/activate)
source ~/llm-service-lab/.venv/Scripts/activate

# 도구 확인
cd "$KIT"
python -m pip install -q -r requirements.txt
python -m pytest -q   # 31 passed, 2 skipped 가 정상(교수 폴더가 있으면 33 passed)

# 견본과 양식을 jobprep으로 복사(이미 있으면 덮어쓰지 않는다)
cd ~/llm-service-lab/jobprep
mkdir -p docs/설계 prototype
cp -n "$KIT"/기준산출물/docs/{요구사항명세서,추적표}.md docs/    # 7장 결과가 없을 때만
cp -n "$KIT"/기준산출물/docs/설계/*.md docs/설계/
cp -n "$KIT/디자인토큰_견본.md" docs/설계/디자인토큰.md
cp -n "$KIT/화면명세_양식.md"   docs/설계/화면명세.md
cp -n "$KIT/접근성점검_양식.md" docs/설계/접근성점검.md
cp -rn "$KIT/prototype_시작/." prototype/

# 대비 점검 → 토큰 변환 → HTML 점검
python "$KIT/tools/contrast.py" docs/설계/디자인토큰.md
python "$KIT/tools/tokens_to_css.py" docs/설계/디자인토큰.md -o prototype/css/tokens.css
python "$KIT/tools/html_check.py" prototype/

# 프로토타입을 브라우저로 본다(웹 포트 8100, 부록 A-16). 끄려면 Ctrl+C
cd prototype && python -m http.server 8100 --bind 127.0.0.1
#   → 브라우저에서 http://localhost:8100/
```

세 도구는 출력을 UTF-8로 내므로, 파이프(`| head`, `| tail`)로 넘겨도 한글이 깨지지 않는다.

## 기대하는 결과

- `pytest -q`: `31 passed, 2 skipped`(교수 폴더가 있으면 `33 passed`).
- 견본을 그대로 `contrast.py`에 넣으면 `미달 1건`이 나오고 종료 코드가 1이다. 핵심 실습에서 고친다.
- `prototype_시작/`은 `html_check.py`를 오류 0건으로 통과한다. 화면을 더한 뒤에도 0건을 유지한다.

## keyboard_walk.py (선택)

Playwright와 브라우저가 필요하다. `requirements.txt`를 설치하면 Playwright 패키지는 들어온다. 브라우저는 내 PC에 있는 것을 쓴다. Windows에 Edge가 있으면 `--channel msedge`, Chrome이 있으면 `--channel chrome`으로 브라우저를 따로 받지 않고 쓴다. 둘 다 없으면 가상 환경을 켠 터미널에서 `python -m playwright install --only-shell chromium`으로 창 없이 쓰는 Chromium을 받는다(부록 A-18. 9장에서 어차피 받는다). 이 도구가 없어도 실습은 사람이 Tab 키로 하는 점검으로 끝낼 수 있다.

```bash
python "$KIT/tools/keyboard_walk.py" prototype/schedule-new.html --tabs 20 --channel msedge
```

## 확인한 환경

2026-11-14, Windows 11, Python 3.13.7, pytest 8.4.2, Playwright 1.64.0, Microsoft Edge 157에서 모든 명령과 테스트를 실행하였다. 같은 날 장 사이 정합 작업에서 pytest 9.2.0, Playwright 1.64.0(Chromium 1248과 Edge)으로 테스트, 대비·HTML 점검, `교수/prototype_e2e.py`를 다시 실행하였다. 2026-11-17에 위 「쓰는 순서」를 Windows 11의 Git Bash(키트 저장소를 흉내 낸 로컬 저장소, Python 3.13.7 가상 환경, pytest 9.2.0)에서 다시 실행하였다. macOS에서는 실행하지 않았다.
