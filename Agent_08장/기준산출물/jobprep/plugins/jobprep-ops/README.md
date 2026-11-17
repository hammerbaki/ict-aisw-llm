# jobprep-ops

`jobprep` 운영팀의 Claude Code 플러그인이다. 운영 기록(`logs/`)으로 장애 보고서를 쓰고 서식을 검사한다.

## 설치

팀 마켓플레이스(`jobprep` 저장소)를 한 번 추가한 뒤 설치한다.

    /plugin marketplace add 「GitHub 아이디」/jobprep
    /plugin install jobprep-ops@jobprep-team

## 구성 요소

| 종류 | 이름 | 부르는 법 |
|---|---|---|
| 스킬 | `incident-report` | `/jobprep-ops:incident-report 2027-09-08`, 또는 "9월 8일 장애 보고서를 써라"처럼 요청하면 모델이 고른다 |

스킬의 스크립트는 `python`(파이썬 3.12 이상)과 표준 라이브러리만 쓴다. Windows의 Git Bash에는 `python3`이 없으므로 `python`으로 부른다.

## 판 기록

| 판 | 바뀐 것 |
|---|---|
| 0.1.0 | 첫 판. incident-report 스킬(서식, 심각도 기준, 요약·검사 스크립트) |
