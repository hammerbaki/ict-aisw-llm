"""공고 검색어의 영문 대소문자를 가리지 않는다 (REQ-JOB-03 보강, 13장 v1.0.1의 수정).

공고 본문에는 SQL, Git, React 같은 영문 기술 이름이 대문자로 섞여 있다. 사용자가 소문자로
검색하면 지금은 한 건도 나오지 않는다. 이 테스트는 수정 전에 실패하고(Red), 수정 뒤에 통과한다(Green).
"""

import pytest

from api import jobs


@pytest.mark.parametrize("word", ["sql", "SQL", "Sql"])
def test_keyword_search_ignores_english_case(client, word):
    expected = client.get("/api/jobs", params={"q": "SQL"}).json()
    found = client.get("/api/jobs", params={"q": word}).json()
    assert len(expected) > 0
    assert [job["id"] for job in found] == [job["id"] for job in expected]


def test_korean_keyword_search_is_unchanged(client):
    found = client.get("/api/jobs", params={"q": "보안"}).json()
    expected = [job["id"] for job in jobs.load_jobs()
                if "보안" in job["title"] + job["company"] + job["description"]]
    assert len(found) > 0
    assert sorted(job["id"] for job in found) == sorted(expected)
