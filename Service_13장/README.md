# Service_13장 키트: 사용성 평가와 서비스 개선

「LLM 서비스 개발」 13장(학사 15주차)의 실습 재료다. 12장까지 만든 `jobprep/`을 동료가 각자의 PC에서 띄워 평가하고, 결과를 이슈로 등록하고, 명세를 고쳐 개선을 풀 리퀘스트로 올린다.

## 받기

키트 저장소에서 받아 저장소 밖 `~/kits/`에 둔다(부록 A-12-3).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits && cp -rn ~/kits-repo/Service_13장 ~/kits/
```

## 들어 있는 것

| 경로 | 무엇 | 쓰는 절 |
|---|---|---|
| `휴리스틱평가_양식.md` | 평가자 한 명의 개별 기록 양식(H1~H10, AI 점검 A1~A6) | 3, 4-4, 11 |
| `휴리스틱통합_양식.md` | 개별 기록을 합친 `휴리스틱.md`의 양식 | 3, 11 |
| `심각도기준표.md` | 0~4 등급, 등급을 정할 때 보는 요소, 우선순위 규칙 | 4, 9 |
| `과업시나리오_양식.md` | 테스트의 목적과 과업 T1~T3, 성공 기준 | 6, 11 |
| `진행자대본_양식.md` | 진행자가 참가자에게 읽어 주는 말과 개입 규칙 | 6, 11 |
| `관찰기록_양식.md` | 기록자가 참가자 한 명마다 쓰는 기록 | 6, 11 |
| `참가동의_양식.md` | 참가자에게 알릴 것과 구두 동의 확인(저장소에 올리지 않음) | 9, 11 |
| `SUS설문_양식.md` | SUS 열 문항의 한국어 번역(집필자 번역)과 응답지 | 8, 11 |
| `사용성테스트_양식.md` | 테스트 결과를 정리한 `사용성테스트.md`의 양식 | 7, 11 |
| `SUS_양식.md` | `SUS.md`의 양식 | 8, 11 |
| `이슈템플릿/usability-problem.md` | 팀 실습 저장소의 `.github/ISSUE_TEMPLATE/`에 넣는 이슈 템플릿 | 10, 11 |
| `풀리퀘스트_양식.md` | 개선 풀 리퀘스트의 설명 양식 | 10, 11 |
| `도구/sus.py` | SUS 점수 계산 | 8 |
| `도구/aggregate.py` | 과업 성공 수준, 시간, 오류 수, 심각도별 문제 수, 우선순위 집계 | 7, 9 |
| `도구/tests/` | 두 도구의 테스트(pytest) | 0, 8 |
| `도구/예시/` | 도구를 시험할 가상 자료(CSV 세 개) | 7, 8, 9 |
| `기준산출물/` | 앞 장의 `jobprep/`이 없는 학습자를 위한 평가 대상 견본(웹 프로토타입, 명세서와 화면 명세 발췌, 페르소나 발췌) | 0, 4-4 |

## 쓰는 순서

1. 0절: 키트를 받고 도구를 테스트한다. 평가 대상(`jobprep/`)을 내 PC에서 띄워 보고, 팀 실습 저장소의 `reviews/ch13/「아이디」/jobprep/`으로 올린다(브랜치 `eval/「아이디」`).
2. 4-4(따라 하기 1): 견본으로 휴리스틱 기록을 연습한다.
3. 8-4(따라 하기 2): 예시 자료로 `sus.py`와 `aggregate.py tasks`를 돌린다.
4. 11절(핵심 실습): 동료 브랜치를 받아 내 PC에서 띄우고 휴리스틱 평가 → 통합과 테스트 준비 → 사용성 테스트 → SUS와 우선순위 → 평가 기록 풀 리퀘스트 → 이슈 3개 → 명세 갱신과 개선 풀 리퀘스트, 재현 절차로 확인 → 개인 저장소에 반영.

## 도구 실행과 테스트

파이썬 3.12 이상. 도구는 표준 라이브러리만 쓴다. 테스트에만 pytest가 필요하다. 가상 환경을 켠 터미널에서 `python`으로 부른다(부록 A-13).

```bash
source ~/llm-service-lab/.venv/Scripts/activate   # macOS: source ~/llm-service-lab/.venv/bin/activate
cd ~/kits/Service_13장/도구
python -m pip install -r requirements.txt
python -m pytest -q tests
python sus.py 예시/sus_예시.csv
python aggregate.py tasks 예시/과업기록_예시.csv
python aggregate.py problems 예시/문제목록_예시.csv
```

기대하는 결과: 테스트 21개 통과(이 테스트는 `교수/` 폴더를 쓰지 않으므로 학생 배포본과 교수 사본이 같다). `sus.py`는 P1 65.0, P2 35.0, P3 75.0, 평균 58.3을 낸다. `aggregate.py problems`의 1~3위는 U-01, U-02, U-03이다. 두 도구는 출력을 UTF-8로 내보내므로 파이프로 넘겨도 한글이 깨지지 않는다.

`--md`를 붙이면 평가 문서에 붙일 마크다운 표를 낸다.

## 견본을 열기

```bash
python -m http.server 8100 --bind 127.0.0.1 --directory ~/kits/Service_13장/기준산출물/jobprep/web
```

브라우저의 시크릿 창에서 `http://localhost:8100/`을 연다(부록 A-16). 다른 프로덕트를 같은 8100으로 열면 브라우저 저장소를 함께 쓰므로, 프로덕트를 바꿀 때마다 시크릿 창을 새로 연다. 견본에는 평가 실습을 위해 사용성 문제를 일부러 남겨 두었다. 평가하기 전에 코드를 읽지 않는다.

## 동료의 프로덕트를 열기

팀 실습 저장소에서 동료의 브랜치를 받아 내 PC에서 띄운다(학생용 11-2).

```bash
cd ~/teams/「팀」-lab
git fetch origin && git switch eval/「동료 아이디」 && git pull
cd reviews/ch13/「동료 아이디」/jobprep
python -m http.server 8100 --bind 127.0.0.1 --directory web     # 정적 웹만 있을 때
# API가 있을 때(api/ 폴더): cp -n .env.example .env  →  python -m uvicorn api.app:app --port 8000
```
