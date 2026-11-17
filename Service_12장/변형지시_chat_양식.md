# 변형 지시: variant-chat (대화형)

> 공통 지시(`변형지시_공통.md`)에 더해 이 변형에만 적용한다.

## 상호작용 방식

대화 화면에 답변을 붙여 넣으면 첫 응답으로 강점, 보완점, 고쳐 쓴 예시를 받는다. 이어서 질문을 보내 피드백을 좁혀 간다(예: "보완점 첫째를 예시로"). 문항과 글자 수 제한은 대화창 위에서 정한다.

## API 계약

- `POST /api/feedback/chat`
- 요청: `{"question": str, "limit": int, "job_id": str | null, "messages": [{"role": "user" | "assistant", "content": str}]}`. `messages`는 대화 전체이고, 첫 사용자 메시지를 자기소개서 답변으로 본다.
- 응답: `{"reply": str, "char_count": int | null, "over_limit": bool | null, "notice": str}`. 첫 응답의 `reply`에는 「강점」, 「보완점」, 「예시」라는 말이 들어간다. 글자 수를 넘으면 `reply`에 「초과」를 밝힌다.
- 오류: LLM 호출 실패는 503과 `detail`

## 파일

- `api/feedback_chat.py`, `web/feedback-chat.html`, `web/feedback-chat.js`, `tests/test_feedback_chat.py`
- 주 메뉴에 「자기소개서 첨삭 대화」를 더한다.
