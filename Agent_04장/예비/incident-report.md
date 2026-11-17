---
description: logs/의 하루치 기록으로 장애 보고서 초안을 쓴다
argument-hint: [YYYY-MM-DD]
disable-model-invocation: true
allowed-tools: Bash(wc *)
---

$ARGUMENTS 날짜의 jobprep 운영 기록으로 장애 보고서 초안을 써라.

- 기록 형식은 @logs/README.md 를 따른다.
- 지금 기록 파일의 줄 수: !`wc -l logs/access.log logs/error.log logs/llm.log`

1. logs/error.log와 logs/access.log에서 $ARGUMENTS 로 시작하는 줄을 읽는다.
2. 같은 오류가 이어진 시간대를 찾는다.
3. 요약, 경과, 원인, 조치 네 부분으로 보고서를 쓴다.
4. docs/운영/장애보고/$ARGUMENTS.md 에 저장한다.

기록에 없는 내용은 추측하지 말고 "확인 필요"로 적어라.
