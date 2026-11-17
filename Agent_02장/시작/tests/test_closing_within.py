"""REQ-JOB-06 마감 임박 필터(closing_within)의 테스트. [학생용 시작 파일]

요구: 사용자가 마감 임박 조건으로 N일을 주면, 시스템은 오늘부터 N일 안에 마감되는 공고만 보여야 한다.
인수 조건: GET /api/jobs?closing_within=7은 0 <= days_left <= 7인 공고만 돌려준다. 마감이 지난 공고는
빠진다. N이 음수이거나 정수가 아니면 422이다. 다른 조건(field, q)과 함께 쓸 수 있다.

기준일은 jobs.today를 바꿔 끼워 고정한다(테스트 더블 가운데 스텁).
data/jobs.json에서 마감이 가장 이른 넷: 20번 2027-09-08, 3번 09-09, 23번 09-14, 6번 09-15.

이 파일은 그대로 실행된다. 「할 일」 표시가 있는 자리를 채운 뒤 동결한다.
"""

from datetime import date

import pytest

from api import jobs

pytestmark = pytest.mark.req(id="REQ-JOB-06")


@pytest.fixture
def on_day(monkeypatch):
    """기준일을 정하는 픽스처. 테스트 안에서 on_day(2027, 9, 1)처럼 부른다."""
    def set_day(year, month, day):
        monkeypatch.setattr(jobs, "today", lambda: date(year, month, day))
    return set_day


def ids(response):
    """응답 목록에서 공고 번호만 순서대로 뽑는다."""
    return [item["id"] for item in response.json()]


# --- 정상 동작 ---------------------------------------------------------------

def test_closing_within_7_returns_jobs_closing_in_7_days(client, on_day):
    on_day(2027, 9, 1)
    response = client.get("/api/jobs", params={"closing_within": 7})
    assert response.status_code == 200
    assert ids(response) == [20]


def test_without_closing_within_returns_all_jobs(client, on_day):
    on_day(2027, 9, 1)
    assert len(client.get("/api/jobs").json()) == 30


# --- 경계값 ------------------------------------------------------------------

@pytest.mark.parametrize("n, expected", [
    (7, [20]),      # 경계: 정확히 7일 뒤 마감은 들어간다
    # 할 일 1: 경계 바로 아래(N=6)와 바로 위(N=8)의 줄을 더한다. 기대값은 위의 마감일 표로 정한다.
], ids=["N=7"])     # 할 일 1: 줄을 더하면 이름(ids)도 더한다
def test_boundary_of_n(client, on_day, n, expected):
    on_day(2027, 9, 1)
    assert ids(client.get("/api/jobs", params={"closing_within": n})) == expected


# 할 일 2: N=0이면 오늘 마감인 공고만 남는지 확인하는 테스트를 쓴다(기준일 2027-09-08).
# 할 일 3: 마감이 지난 공고가 빠지는지 확인하는 테스트를 쓴다(기준일 2027-09-10, N=5).


# --- 다른 조건과 함께 ---------------------------------------------------------

# 할 일 4: field="백엔드 개발"과 함께 쓴 경우의 테스트를 쓴다(기준일 2027-09-01, N=14).
# 할 일 6(선택): q="신입"과 함께 쓴 경우의 테스트를 쓴다(기준일 2027-09-01, N=14).


# --- 잘못된 입력 --------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "-1",
    # 할 일 5: 정수가 아닌 값(글자, 소수, 빈 값)을 더한다.
], ids=["negative"])
def test_invalid_n_is_422(client, bad):
    assert client.get("/api/jobs", params={"closing_within": bad}).status_code == 422


# 할 일 7(선택): tmp_path로 마감일만 다른 작은 공고 자료를 만들고, jobs.list_jobs(closing_within=7)를
#              함수 단위로 확인하는 테스트를 쓴다(강의안 4-4절의 small_jobs 픽스처).
