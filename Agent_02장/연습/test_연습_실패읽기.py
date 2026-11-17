"""[연습] pytest의 실패 화면 읽기. 일부러 틀리게 쓴 테스트 네 개이다.

저장소의 tests/에 복사해 실행하고, 화면을 읽은 뒤 바로 지운다. 동결하기 전에 지운다.

    cp ~/kits/Agent_02장/연습/test_연습_실패읽기.py tests/
    pytest tests/test_연습_실패읽기.py
    rm tests/test_연습_실패읽기.py
"""

import pytest

from api import jobs


def test_목록_비교(client):
    # AI 서비스 분야 공고의 번호. 기대값의 순서를 일부러 틀리게 적었다.
    items = client.get("/api/jobs", params={"field": "AI 서비스"}).json()
    assert [item["id"] for item in items] == [7, 12, 19, 14]


def test_사전_비교(client):
    # 건강 확인 응답. 공고 수를 일부러 틀리게 적었다.
    assert client.get("/api/health").json() == {"status": "ok", "llm_fake": True, "jobs": 31}


def test_예외_기대():
    # 마감일이 올바른 공고는 예외를 내지 않는다. 예외를 기대한 것이 틀렸다.
    with pytest.raises(ValueError):
        jobs.days_left({"deadline": "2027-09-08"})


def test_픽스처_이름_오타(clinet):
    # 픽스처 이름을 잘못 썼다(client → clinet). 실패(FAILED)가 아니라 오류(ERROR)가 된다.
    assert clinet.get("/api/health").status_code == 200
