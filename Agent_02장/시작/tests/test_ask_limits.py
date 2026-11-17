"""REQ-ASK-06 질문의 길이 제한 테스트. [학생용 시작 파일]

요구: 만약 질문이 비어 있거나 500자를 넘으면, 시스템은 검색과 LLM 호출 없이 422로 응답해야 한다.
인수 조건: 빈 문자열, 공백만 있는 문자열, 501자 문자열은 422이다. 500자는 받아들인다.

검색 함수와 LLM 호출을 unittest.mock.Mock(wraps=...)로 감싸 불렸는지 확인한다.
wraps를 쓰면 진짜 함수가 그대로 실행되고, 호출 기록만 남는다.

이 파일은 그대로 실행된다. 「할 일」 표시가 있는 자리를 채운 뒤 동결한다.
"""

from unittest.mock import Mock

import pytest

from api import ask, llm

pytestmark = pytest.mark.req(id="REQ-ASK-06")

MAX_CHARS = 500


@pytest.fixture
def watched(monkeypatch):
    """ask.search와 llm.complete를 기록하는 Mock으로 바꿔 끼운다."""
    search = Mock(wraps=ask.search)
    complete = Mock(wraps=llm.complete)
    monkeypatch.setattr(ask, "search", search)
    monkeypatch.setattr(llm, "complete", complete)
    return search, complete


@pytest.mark.parametrize("question", [
    "",
    # 할 일 1: 공백만 있는 질문과 501자 질문을 더한다.
], ids=["empty"])
def test_rejected_question_is_422_without_search_or_llm(client, watched, question):
    search, complete = watched
    response = client.post("/api/ask", json={"question": question})
    assert response.status_code == 422
    search.assert_not_called()
    complete.assert_not_called()


# 할 일 2: 500자 질문은 받아들이고(200) 검색이 한 번 불리는지 확인하는 테스트를 쓴다.
#          search.assert_called_once()를 쓴다.
