"""작업 카드 T1(REQ-JOB-07 고용 형태 필터)의 인수 검사.

판정 도구(judge.py)가 실험 저장소의 tests/에 잠시 복사해 돌리고 지운다.
기준 자료(data/jobs.json): 정규직 16건, 인턴 11건, 계약직(1년, 전환 검토) 3건. AI 서비스 분야의 정규직 2건.
"""


def employment(client, **params):
    return client.get("/api/jobs", params=params)


def test_full_time_only(client):
    items = employment(client, employment_type="정규직").json()
    assert len(items) == 16
    assert all(item["employment_type"] == "정규직" for item in items)


def test_intern_only(client):
    items = employment(client, employment_type="인턴").json()
    assert len(items) == 11


def test_contract_matches_by_prefix(client):
    items = employment(client, employment_type="계약직").json()
    assert len(items) == 3
    assert all(item["employment_type"].startswith("계약직") for item in items)


def test_combines_with_field(client):
    items = employment(client, employment_type="정규직", field="AI 서비스").json()
    assert len(items) == 2


def test_unknown_type_is_empty(client):
    response = employment(client, employment_type="프리랜서")
    assert response.status_code == 200
    assert response.json() == []


def test_empty_value_is_422(client):
    assert employment(client, employment_type="").status_code == 422
