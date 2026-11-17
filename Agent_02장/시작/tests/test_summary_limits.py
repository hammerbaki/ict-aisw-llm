"""REQ-SUM-05 요약 본문의 길이 제한 테스트. [학생용 시작 파일]

요구: 만약 요약할 본문이 비어 있거나 4,000자를 넘으면, 시스템은 LLM을 부르지 않고 422로 응답해야 한다.
인수 조건: 빈 문자열, 공백만 있는 문자열, 4,001자 문자열은 422이다. 4,000자는 받아들인다.

"LLM을 부르지 않고"는 상태 코드만으로 확인할 수 없다. llm.complete를 스파이로 바꿔 끼워
불린 횟수를 센다.

이 파일은 그대로 실행된다. 「할 일」 표시가 있는 자리를 채운 뒤 동결한다.
"""

import pytest

from api import llm

pytestmark = pytest.mark.req(id="REQ-SUM-05")

MAX_CHARS = 4000


@pytest.fixture
def llm_calls(monkeypatch):
    """llm.complete를 감싸는 스파이. 진짜 함수(모의 모드)를 그대로 부르고, 부를 때마다 task를 기록한다."""
    calls = []
    real_complete = llm.complete

    def spy(system, prompt, task):
        calls.append(task)
        return real_complete(system, prompt, task)

    monkeypatch.setattr(llm, "complete", spy)
    return calls


@pytest.mark.parametrize("text", [
    "",
    # 할 일 1: 공백만 있는 문자열과 4,001자 문자열을 더한다. 4,001자는 "가" * (MAX_CHARS + 1)로 만든다.
], ids=["empty"])
def test_rejected_text_is_422_without_calling_llm(client, llm_calls, text):
    response = client.post("/api/summary", json={"text": text})
    assert response.status_code == 422
    assert llm_calls == []


def test_text_of_4000_chars_is_accepted(client, llm_calls, job_text):
    text = (job_text * 20)[:MAX_CHARS]
    assert len(text) == MAX_CHARS
    response = client.post("/api/summary", json={"text": text})
    assert response.status_code == 200
    assert llm_calls == ["summary"]
