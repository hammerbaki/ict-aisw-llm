# 5장 키트: 명세 기반 구현과 배포

「LLM 서비스 개발」 5장(학사 6주차)의 실습 재료이다. 강의안은 `Service_05장_학생용.md`이다. 4장에서 쓴 요구사항 명세서로 공고 모아보기 웹을 정적 웹으로 구현하고, 인수 조건으로 점검한 뒤 GitHub Pages에 배포한다. EARS 검사기는 4장 키트(`Service_04장/도구/ears_check.py`)의 것을 쓴다.

## 받는 법

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Service_05장 ~/kits/
```

키트 저장소의 클론은 부록 A-12-2, 장마다 받는 법은 부록 A-12-3에 있다. 키트 폴더는 원본 사본으로 두고, 쓸 파일은 `~/llm-service-lab/ch05/`로 복사한다.

## 들어 있는 것

| 경로 | 무엇 | 쓰는 절 |
|---|---|---|
| `xml2json.py` | 고용24 채용정보 목록 응답(XML)을 화면용 JSON으로 바꾼다. `KEEP`의 항목만 남기고, 빈 값과 날짜가 아닌 마감일을 보고한다. 표준 라이브러리만 쓴다 | 8-2 |
| `견본/응답_지어낸것.xml` | **지어낸** 목록 응답 10건. 항목 이름은 고용24 개발명세서(2026-11-18 확인)를 따랐고 회사, 공고, 값, 주소는 모두 지어낸 것이다. 4장 키트의 같은 이름 파일과 같다 | 8-2(인증키가 늦을 때) |
| `서버확인/index.html`, `서버확인/data/jobs.json` | 같은 폴더의 `data/jobs.json`을 읽어 건수만 보이는 쪽. `jobs.json`은 위 견본을 `xml2json.py`로 바꾸고 출처를 「지어낸 견본」으로 고친 것이다 | 4-2, 4-3(따라 하기 2) |
| `도구/predeploy.py` | 배포 전 점검. 공개할 폴더를 읽기만 하고, 웹에 쓰지 않는 파일, `WORK24_KEY`의 값, 키와 개인 정보의 꼴, 자료 파일의 `busino`, `/`로 시작하는 경로를 찾는다 | 8-7 |
| `양식/빈틈_양식.md` | 계획에서 받은 「명세가 정하지 않은 것」과 내 판단 | 8-3, 8-6 |
| `양식/인수조건_양식.md` | 인수 조건 표(Given-When-Then, 내 판정, 에이전트, 다르면 까닭) | 8-4, 8-5 |
| `tests/test_xml2json.py` | 변환 프로그램과 점검 도구의 테스트 7개 | 0절 |
| `requirements.txt` | 테스트에 쓰는 pytest의 판 | 0절 |
| `교수/` | 교수 전용: 견본 구현(`견본_web/`, 4장 키트 `교수/명세_예시`의 REQ-01~13), 그 판정 함수를 센 `check_app.js`. 학생용 키트 저장소에는 넣지 않는다 | |

## 쓰는 순서

가상 환경을 켠 터미널에서 실행한다(부록 A-13). Windows에서는 `export PYTHONUTF8=1`도 한 번 해 둔다. 인증키는 `~/work24.env`에 `export WORK24_KEY=…` 꼴로 둔다(4장 3-3).

1. 0절: `cd ~/kits/Service_05장 && python -m pytest -q` → `7 passed`.
2. 4-3: `mkdir -p ch05 && cp -rn ~/kits/Service_05장/서버확인 ch05/` 뒤 `python -m http.server 8100 --bind 127.0.0.1 --directory ch05/서버확인`. 다른 터미널에서 `curl`로 `200`, `200`, `404`를 본다. 포트는 부록 A-16의 약속(웹 서버 8100)을 따른다.
3. 8-2: `cp -n ~/kits/Service_05장/xml2json.py ch05/` 뒤 `python ch05/xml2json.py ch04/응답_견본.xml ch05/web/data/jobs.json`.
4. 8-3~8-6: 양식 둘을 `ch05/빈틈.md`, `ch05/인수조건.md`로 복사해 쓴다.
5. 8-7: 공개 저장소 폴더에 `web/`의 내용을 복사한 뒤 `python ~/kits/Service_05장/도구/predeploy.py ~/jobs-board`. `PREDEPLOY_OK`가 나오면 푸시한다.

## 실행 확인 (2026-11-18)

Windows 11, Git Bash, Python 3.13.7, pytest 9.2.0, curl 8.21.0, Node.js 24.14.0. 스크래치 폴더에 `HOME`을 따로 두고 강의안의 명령을 그대로 실행하였다. 인증키는 `FAKE`로 시작하는 가짜 값을 썼다.

| 명령 | 결과 |
|---|---|
| `python -m pytest -q` (학생 키트, 교수용 사본) | `7 passed` |
| `python xml2json.py 견본/응답_지어낸것.xml …/jobs.json` | `공고 10건`, `빈 값: {'sal': 1}`, `날짜가 아닌 closeDt: ['채용시까지']` |
| `python -m http.server 8100 --bind 127.0.0.1 --directory ch05/서버확인`과 `curl -w "%{http_code} %{content_type}"` | `/` 200 text/html, `/data/jobs.json` 200 application/json, `/nothing.html` 404. 서버 기록 네 줄 |
| `교수/견본_web`을 같은 방법으로 띄우고 `curl` | `/`, `/app.js`, `/style.css`, `/data/jobs.json` 모두 200 |
| `node 교수/check_app.js` | 앞 두 장 사아자전자·새솔디자인, 임박 D-1·D-2·D-3, 광주 4, 개발 2, 우주 0, 상시 2, 급여 빈 값 1 |
| `predeploy.py ~/jobs-board` (로컬 `git init` 폴더에 견본 구현을 복사) | `PREDEPLOY_OK 4 files`. 인증키를 적은 메모 파일을 넣으면 멈춤(종료 코드 1) |
| 지역에 「광주」가 든 공고 세기(8-4의 `python -c`) | `4` |

실행하지 않은 것: 실제 고용24 응답으로의 변환, 브라우저 화면(`file://`과 `http://`의 차이), Claude Code의 계획과 구현, Aside의 점검, `gh repo create`와 GitHub Pages의 실제 배포. 교수용 강의안의 「확인한 것과 확인하지 못한 것」을 본다.
