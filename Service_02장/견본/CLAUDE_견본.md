# llm-service-lab

「LLM 서비스 개발」 개인 실습 저장소이다. 장마다 폴더(`ch01/`, `ch02/`, ...)를 두고, 6장부터 공통 사례는 `jobprep/`에 둔다.

## 실행 명령

- 가상 환경: 저장소 맨 위의 `.venv`. Claude Code는 가상 환경을 켠 터미널에서 시작한다(Windows `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`). 파이썬은 `python`으로 부른다.
- `python`이 가상 환경의 것이 아니면(`No module named pytest`) Windows는 `.venv/Scripts/python`, macOS는 `.venv/bin/python`으로 부른다.
- 2장 프로그램 실행: `cd ch02/deadline && python deadline.py --today 2027-03-15`
- 2장 테스트: `cd ch02/deadline && python -m pytest -q`

## 작업 규칙

- 파일을 고치기 전에 바꿀 파일과 바꿀 내용을 먼저 목록으로 말한다.
- 기능 하나를 고칠 때 그 기능의 테스트를 함께 고치거나 추가하고, 테스트를 실행해 결과를 보여 준다.
- 답과 주석은 한국어로 쓴다.

## 커밋 메시지 규칙

- 제목 한 줄은 50자 이내로, 무엇을 바꾸었는지 명사형으로 끝낸다(예: `출력 순서를 마감일 순으로 정렬`).
- 까닭이 필요하면 빈 줄 뒤 본문에 적는다.
- 커밋 하나에는 변경 하나만 넣는다.

## 금지 사항

- git commit, git push, git reset, git revert는 사람이 지시할 때만 한다.
- `.env`, 토큰, 비밀번호가 든 파일은 읽거나 만들지 않는다.
- 다른 장의 폴더(`ch01/` 등)는 지시 없이 고치지 않는다.
