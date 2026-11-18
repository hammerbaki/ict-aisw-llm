# 8장 실습 키트: 네트워크 동작의 분석과 API 구현

「LLM 서비스 개발」 8장(학사 10주차, 서비스 3: 예약·일정 웹앱의 둘째 장)의 실습 재료이다. 강의안 `Service_08장_학생용.md`의 0절에서 키트 저장소(`~/kits-repo`, 부록 A-12)로부터 이 폴더를 `~/kits/Service_08장/`로 받는다. 키트 폴더 자체는 저장소에 넣지 않는다.

```bash
git -C ~/kits-repo pull && cp -rn ~/kits-repo/Service_08장 ~/kits/
python -m pip install -r ~/kits/Service_08장/requirements.txt
```

## 들어 있는 것

| 경로 | 무엇인가 | 쓰는 절 |
|---|---|---|
| `예제웹앱/server.py`, `static/` | 스터디룸 예약 예제 웹앱. 파이썬 표준 라이브러리만 쓴다. `python server.py`로 띄우고 `http://localhost:8200/`을 연다 | 1-4, 7-2, 7-7 |
| `예제웹앱/test_server.py` | 예제 웹앱의 끝점 테스트(키트 점검용) | 교수의 수업 전 점검 |
| `견본/session_견본.har` | 예제 웹앱에 실제로 보낸 요청 13건과 응답의 기록(HAR 1.2). 아래 「견본 HAR」 참고 | 1-5, 1-6, 5-2 |
| `har_list.py` | HAR의 `/api/` 요청을 순서대로 보이고 (메서드, 경로, 상태 코드)로 묶어 센다 | 1-6, 7-3 |
| `replay.py` | HAR의 `/api/` 요청을 내 서버에 같은 순서로 보내 상태 코드를 견준다 | 5-2, 7-7 |
| `견본서버/app.py`, `test_app.py` | 강의안 2-3의 명세로 만든 FastAPI 서버와 테스트 다섯 개 | 4절, 5-1, 7-6 |
| `요청본문/*.json` | `curl --data-binary @파일`로 보낼 본문 다섯 개(정상, 겹침, 틀린 형식, 앞뒤가 바뀐 시각, 맞닿은 시각) | 4절, 7-7 |
| `공개API/jobs_api.py`, `test_jobs_api.py`, `응답_지어낸것.xml` | 고용24 채용정보를 서버가 부르는 끝점, 가짜 응답을 쓰는 테스트 다섯 개, 4·5장과 같은 지어낸 견본 응답(공고 10건) | 3-4, 7-9 |
| `requirements.txt` | FastAPI, Uvicorn, httpx, pytest의 판 | 0절 |

## 포트

부록 A-16의 약속대로 학습자가 만드는 API 서버(견본 서버 포함)는 8000을 쓴다. 예제 웹앱은 두 서버를 함께 띄워 견주기 위해 8200을 쓴다(`python server.py 8201`처럼 바꿀 수 있다). 두 서버 모두 `127.0.0.1`에서만 받는다.

## 견본 HAR

`견본/session_견본.har`는 **브라우저에서 내보낸 것이 아니다.** 집필 환경에서는 Chrome 개발자 도구의 HAR 내보내기를 조작할 수 없어서, `교수/견본HAR_만들기.py`(학생 배포본에는 없다)로 강의안 7-2의 조작 순서(화면 열기 → 목록 읽기 → 10:00~11:00 예약 → 10:30~11:30 예약 → 취소 → 다른 탭에 남은 목록에서 같은 예약을 다시 취소)대로 화면이 보내는 요청을 같은 순서로 예제 웹앱에 보내고, 받은 응답을 HAR 1.2의 필수 항목으로 기록하였다. 응답은 예제 웹앱이 실제로 돌려준 것이다. Chrome의 HAR와 다른 점: 머리글이 적다, 시간을 `wait`에 모았다, `pages`와 `_initiator` 같은 밑줄 항목이 없다.

같은 조작(두 탭의 재취소는 빼고)을 집필 환경의 내장 브라우저로 화면에서 해 보았다(2026-11-18). 날짜를 고른 뒤 브라우저가 보낸 `/api/` 요청의 순서와 상태 코드(POST 201 → GET 200 → POST 409 → GET 200 → DELETE 204 → GET 200)가 견본과 같았다. 화면을 처음 열 때 오늘 날짜의 목록을 한 번 더 읽는 점만 다르다. 내장 브라우저의 네트워크 기록은 204 응답에 `net::ERR_ABORTED` 표시를 붙였으나 화면은 204를 받아 「취소하였다」를 보였다. Chrome 개발자 도구에서도 그렇게 보이는지는 확인하지 못하였다.

## 실행 확인의 기록 (2026-11-18)

집필용 PC(Windows 11, Git Bash, Python 3.13.7, FastAPI 0.163.2, Pydantic 2.14.3, Uvicorn 0.54.0, httpx 0.28.1, pytest 9.2.0, curl 8.21.0)에서 실행하였다.

| 명령 | 결과 |
|---|---|
| 키트 폴더에서 `python -m pytest -q -p no:cacheprovider` | 15 passed, 1 warning(`starlette`의 `httpx` 사용 방식 변경 예고) |
| `견본서버/`에서 같은 명령 | 5 passed, 1 warning |
| `공개API/`에서 같은 명령 | 5 passed, 1 warning |
| `예제웹앱/`에서 같은 명령 | 5 passed |
| `python server.py` 뒤 `curl`로 다섯 끝점 | 200, 201, 409, 422(날짜 꼴, 앞뒤가 바뀐 시각), 204, 404 |
| `python har_list.py 견본/session_견본.har` | `/api/` 요청 10건, 묶음 여섯 행 |
| 견본 서버를 새로 띄운 뒤 `python replay.py 견본/session_견본.har http://127.0.0.1:8000` | 같다 10건, 다르다 0건(약 2초) |
| 같은 명령에 `http://localhost:8000` | 결과는 같으나 약 22초. Windows에서 `localhost`가 IPv6를 먼저 시도하기 때문이다 |

알게 된 것:

- Windows의 Git Bash에서 `curl -d '…한글…'`로 보내면 본문이 UTF-8이 아닌 코드 페이지로 바뀌어 간다(curl 8.21.0 mingw판). 견본 서버(FastAPI)는 400 「There was an error parsing the body」, 예제 웹앱은 422 「본문이 UTF-8의 JSON이 아니다」를 돌려주었다. 그래서 본문을 `요청본문/`의 파일로 두고 `--data-binary @파일`로 보낸다.
- 파이썬이 Git Bash로 한글을 출력하면 깨지므로 `har_list.py`, `replay.py`, `server.py`는 `sys.stdout.reconfigure(encoding="utf-8")`를 한다.
- 예제 웹앱의 204 응답에는 `Content-Length`를 보내지 않는다(RFC 9110 8.6).

`-p no:cacheprovider`는 키트 폴더에 `.pytest_cache`를 남기지 않게 한다.

## 견본 응답에 대하여

`공개API/응답_지어낸것.xml`은 4·5장 키트의 견본과 같은 파일이다. 항목 이름은 고용24 OPEN-API 채용정보 개발명세서를 따랐으나 회사, 공고, 값은 모두 지어낸 것이다. 실제 응답의 바깥 구조, 날짜의 꼴, 빈 값은 실제 응답으로 확인하지 못하였다(개편안의 U2). 테스트의 인증키는 `FAKE_KEY_123`이라는 가짜 값이다.
