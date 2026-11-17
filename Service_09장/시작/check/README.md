# 자동 검사 (jobprep/web/check/)

인수 조건(`jobprep/docs/인수조건.md`) 가운데 기계가 확인할 수 있는 것을 확인한다.
이 폴더는 공개 폴더(`_site`)에 들어가지 않는다(`jobprep/tools/predeploy.py`가 뺀다).

| 파일 | 하는 일 | 필요한 것 |
|---|---|---|
| `check_static.py` | 파일, 공고 자료, HTML 구조, 식별자, 경로, 레이블, 금지 사항 | 파이썬 표준 라이브러리만 |
| `check_browser.py` | 화면을 브라우저로 열어 누르고 입력해 인수 조건의 Then 을 확인 | `playwright` 와 Chromium |

## 실행

가상 환경(`~/llm-service-lab/.venv`)을 켠 터미널에서 실행한다(부록 A-13). Windows Git Bash는 `source ~/llm-service-lab/.venv/Scripts/activate`, macOS는 `source ~/llm-service-lab/.venv/bin/activate`로 켠다.

```bash
cd ~/llm-service-lab/jobprep/web
python check/check_static.py
python -m pip install -r check/requirements.txt                    # 처음 한 번
python -m playwright install --only-shell chromium                 # 처음 한 번(부록 A-18)
python check/check_browser.py
python check/check_browser.py AC-009-1       # 하나만
python check/check_browser.py --headed       # 창을 띄워 보며
```

## 정적 검사 번호와 인수 조건

| 정적 검사 | 확인하는 것 | 관련 인수 조건 |
|---|---|---|
| S-01 | 화면 파일 4개와 `data/jobs.json`이 있다(index=SCR-01, detail=SCR-02, saved=SCR-07, schedule=SCR-03·04) | 모든 인수 조건의 전제 |
| S-02 | 공고 30건, 번호가 겹치지 않음, 항목과 날짜 형식 | AC-002-1의 전제 |
| S-03 | `lang="ko"`, `<title>`, viewport | AC-035-1 보조 |
| S-04 | 화면 명세 「검사용 약속」의 id | 브라우저 검사 전체의 전제 |
| S-05 | 상대 경로, 연결 대상 파일 | 배포 뒤 깨짐 예방 |
| S-06 | 입력 요소마다 레이블 | AC-036-1 |
| S-07 | 비밀 정보, innerHTML, 외부 요청 | AC-039-1 보조 |
| S-08 | 메모의 개인 정보 안내 | AC-039-2 |

## 검사가 보증하지 않는 것

- 화면이 보기 좋은가, 글이 읽기 쉬운가, 사용자가 길을 잃지 않는가(13장의 사용성 평가).
- 키보드만으로 쓸 수 있는가, 실제 폰에서 열리는가(손 점검 AC-033-1, AC-035-2).
- 검사가 고르지 않은 입력에서의 동작. 검사는 정해 둔 예 몇 개만 본다.
