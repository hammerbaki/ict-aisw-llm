# 변형 지시: variant-form (양식형)

> 공통 지시(`변형지시_공통.md`)에 더해 이 변형에만 적용한다.

## 상호작용 방식

한 화면에서 지원 공고(선택), 문항, 글자 수 제한, 답변을 입력하고 「피드백 받기」 한 번으로 결과를 받는다. 결과는 강점, 보완점, 고쳐 쓴 예시의 세 칸으로 나누어 보인다.

## API 계약

- `POST /api/feedback`
- 요청: `{"question": str, "answer": str, "limit": int, "job_id": str | null}`
- 응답: `{"strengths": [str], "improvements": [str], "rewrite": str, "char_count": int, "limit": int, "over_limit": bool, "notice": str}`
- 오류: 답변이 50자 미만이면 400과 `detail`, LLM 호출 실패는 503과 `detail`

## 파일

- `api/feedback.py`, `web/feedback.html`, `web/feedback.js`, `tests/test_feedback_form.py`
- 주 메뉴에 「자기소개서 피드백」을 더한다.
