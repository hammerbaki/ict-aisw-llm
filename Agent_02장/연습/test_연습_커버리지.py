"""[연습] 단언이 없는 테스트도 커버리지를 올린다.

이 파일의 테스트는 엔드포인트를 부르기만 하고 결과를 확인하지 않는다. 커버리지는 오르지만
코드가 틀려도 통과한다. 저장소의 tests/에 복사해 실행하고, 읽은 뒤 바로 지운다.

    cp ~/kits/Agent_02장/연습/test_연습_커버리지.py tests/
    coverage run -m pytest -q tests/test_연습_커버리지.py
    coverage report --include="api/jobs.py"
    rm tests/test_연습_커버리지.py
"""


def test_부르기만_한다(client):
    client.get("/api/jobs")
    client.get("/api/jobs", params={"field": "웹 개발", "q": "신입"})
    client.get("/api/jobs", params={"closing_within": 7})
    client.get("/api/jobs/1")
    client.get("/api/jobs/999")
