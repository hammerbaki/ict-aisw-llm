"""브라우저 검사: 인수 조건(AC)을 실제 브라우저(Playwright, Chromium)로 확인한다.

이 스크립트는 웹 폴더를 로컬 서버(127.0.0.1, 빈 포트)로 띄우고, 화면을 열어 누르고
입력한 뒤, 인수 조건의 Then 이 화면에 나타나는지 본다. 인수 조건 하나가 함수 하나다.
각 인수 조건은 새 브라우저 문맥(context)에서 시작하므로 앞 검사의 저장소가 남지 않는다.
인수 조건 번호는 AC-<요구 번호 세 자리>-<순번>이다(명세 v3, 9장 인수 조건 표).

가상 환경(~/llm-service-lab/.venv)을 켠 터미널에서 실행한다(부록 A-13).

    cd ~/llm-service-lab/jobprep/web
    python check/check_browser.py                    모든 인수 조건
    python check/check_browser.py AC-008-1 AC-009-1  지정한 것만
    python check/check_browser.py --headed           창을 띄워 보며 실행

준비: python -m pip install -r check/requirements.txt
      python -m playwright install --only-shell chromium     (부록 A-18)
종료 코드: 모두 통과하면 0, 하나라도 실패하면 1.
"""
import datetime
import functools
import http.server
import json
import re
import sys
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

WEB = Path(__file__).resolve().parents[1]
JOBS = json.loads((WEB / "data" / "jobs.json").read_text(encoding="utf-8"))["jobs"]
TIMEOUT = 5000  # 밀리초. 화면이 바뀌기를 기다리는 최대 시간

CHECKS = []


def ac(code, title):
    """인수 조건 하나를 검사 함수로 등록한다."""
    def register(fn):
        CHECKS.append((code, title, fn))
        return fn
    return register


# ---------- 기대값 계산 (명세를 파이썬으로 옮긴 것) ----------

TODAY = "2027-05-17"   # 검사용 기준일. 화면은 주소의 ?today= 로 이 날을 오늘로 본다(화면 명세의 검사용 약속)


def by_deadline(job):
    """REQ-002: 접수 마감일이 가까운 순. 마감일이 없는 상시 공고는 맨 뒤(검사용 약속)."""
    return (job["deadline"] is None, job["deadline"] or "", job["id"])


def expected_ids(keyword="", category="", region=""):
    """명세 REQ-002, REQ-006, REQ-028 을 그대로 계산한 기대 결과(마감일 순 공고 번호)."""
    out = []
    for job in JOBS:
        text = f"{job['title']} {job['company']}".lower()   # REQ-006: 제목이나 모집기관
        if keyword and keyword.lower() not in text:
            continue
        if category and job["category"] != category:
            continue
        if region and job["region"] != region:
            continue
        out.append(job)
    return [j["id"] for j in sorted(out, key=by_deadline)]


def expected_badge(deadline, today=TODAY):
    """REQ-003: 0~3일 남으면 '마감 임박 D-N'(0일은 D-day), 지난 마감은 '마감', 그 밖과 상시는 표시 없음."""
    if deadline is None:
        return None
    left = (datetime.date.fromisoformat(deadline) - datetime.date.fromisoformat(today)).days
    if left < 0:
        return "마감"
    if left <= 3:
        return "마감 임박 D-day" if left == 0 else f"마감 임박 D-{left}"
    return None


def shown_ids(page):
    return page.locator(".job-card").evaluate_all("els => els.map(e => e.dataset.jobId)")


def count_in_text(text):
    m = re.search(r"(\d+)\s*건", text)
    return int(m.group(1)) if m else None


def save_job(page, base, job_id):
    """상세 화면에서 관심 공고로 저장한다(Given 을 만드는 도우미)."""
    page.goto(base + f"detail.html?id={job_id}")
    expect(page.locator("#save-toggle")).to_have_text("관심 공고 저장", timeout=TIMEOUT)
    page.click("#save-toggle")
    expect(page.locator("#save-toggle")).to_have_text("관심 해제", timeout=TIMEOUT)


def add_schedule(page, job_id, stage, date, memo=""):
    page.select_option("#schedule-job", job_id)
    page.select_option("#schedule-stage", stage)
    page.fill("#schedule-date", date)
    page.fill("#schedule-memo", memo)
    page.click("#schedule-form [type=submit]")


# ---------- 인수 조건: SCR-01 공고 목록 (index.html) ----------

@ac("AC-002-1", "목록 화면에 공고 30건이 마감일 순(상시는 맨 뒤)으로 보인다")
def ac_002_1(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    assert shown_ids(page) == expected_ids(), "카드의 순서가 마감일 순이 아니다"


@ac("AC-003-1", "기준일 2027-05-17 의 목록에서 모든 카드의 마감 표시가 명세 REQ-003 과 같다")
def ac_003_1(page, base):
    page.goto(base + f"index.html?today={TODAY}")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    wrong = []
    for job in JOBS:
        badge = page.locator(f".job-card[data-job-id='{job['id']}'] .deadline-badge")
        want = expected_badge(job["deadline"])
        got = badge.inner_text().strip() if badge.count() else None
        if got != want:
            wrong.append(f"{job['id']}(마감 {job['deadline']}): 기대 {want}, 실제 {got}")
    assert not wrong, "; ".join(wrong[:3])


@ac("AC-006-1", "검색어 '데이터'를 넣으면 제목이나 기업에 그 말이 든 공고만 보인다")
def ac_006_1(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    page.fill("#search-input", "데이터")
    want = expected_ids(keyword="데이터")
    expect(page.locator(".job-card")).to_have_count(len(want), timeout=TIMEOUT)
    assert shown_ids(page) == want, f"보이는 공고가 다르다: {shown_ids(page)}"


@ac("AC-007-1", "맞는 공고가 없으면 카드가 없고 빈 상태 안내가 보인다")
def ac_007_1(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    page.fill("#search-input", "없는공고검색어")
    expect(page.locator(".job-card")).to_have_count(0, timeout=TIMEOUT)
    expect(page.locator("#empty-state")).to_be_visible()
    expect(page.locator("#empty-state")).to_contain_text("조건에 맞는 공고가 없습니다")


@ac("AC-007-2", "빈 상태에서 '조건 초기화'를 누르면 다시 30건이 보이고 검색어가 비워진다")
def ac_007_2(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    page.select_option("#filter-region", "부산")
    page.fill("#search-input", "없는공고검색어")
    expect(page.locator("#empty-state")).to_be_visible(timeout=TIMEOUT)
    page.click("#reset-filters")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    expect(page.locator("#search-input")).to_have_value("")
    expect(page.locator("#empty-state")).to_be_hidden()


@ac("AC-028-1", "지역 '부산'을 고르면 그 지역 공고만 보인다")
def ac_028_1(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    page.select_option("#filter-region", "부산")
    want = expected_ids(region="부산")
    expect(page.locator(".job-card")).to_have_count(len(want), timeout=TIMEOUT)
    assert shown_ids(page) == want


@ac("AC-028-2", "직무 분야 'AI서비스'를 고르면 그 분야 공고만 보인다")
def ac_028_2(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    page.select_option("#filter-category", "AI서비스")
    want = expected_ids(category="AI서비스")
    expect(page.locator(".job-card")).to_have_count(len(want), timeout=TIMEOUT)
    assert shown_ids(page) == want


@ac("AC-029-1", "표시된 공고 수가 보이는 카드 수와 같다(검색 전후 모두)")
def ac_029_1(page, base):
    page.goto(base + "index.html")
    expect(page.locator(".job-card")).to_have_count(30, timeout=TIMEOUT)
    assert count_in_text(page.inner_text("#result-count")) == 30, page.inner_text("#result-count")
    page.fill("#search-input", "개발자")
    n = len(expected_ids(keyword="개발자"))
    expect(page.locator(".job-card")).to_have_count(n, timeout=TIMEOUT)
    assert count_in_text(page.inner_text("#result-count")) == n, page.inner_text("#result-count")


# ---------- 인수 조건: SCR-02 공고 상세 (detail.html) ----------

@ac("AC-030-1", "공고를 누르면 상세 화면으로 가고 제목·기업·자격 요건이 자료와 같다")
def ac_030_1(page, base):
    page.goto(base + "index.html")
    first = page.locator(".job-card").first
    expect(first).to_be_visible(timeout=TIMEOUT)
    job_id = first.get_attribute("data-job-id")
    job = next(j for j in JOBS if j["id"] == job_id)
    first.locator("a").first.click()
    page.wait_for_url(re.compile(r"detail\.html\?id=" + job_id))
    expect(page.locator("#job-title")).to_have_text(job["title"], timeout=TIMEOUT)
    expect(page.locator("#job-company")).to_have_text(job["company"])
    for text in job["requirements"]:
        expect(page.locator("#job-detail")).to_contain_text(text)


@ac("AC-003-2", "마감 2일 전 공고의 상세 화면에 '마감 임박 D-2'가 보인다")
def ac_003_2(page, base):
    job = next(j for j in JOBS if expected_badge(j["deadline"]) == "마감 임박 D-2")
    page.goto(base + f"detail.html?id={job['id']}&today={TODAY}")
    expect(page.locator("#job-detail .deadline-badge")).to_have_text("마감 임박 D-2", timeout=TIMEOUT)


@ac("AC-037-1", "없는 공고 번호로 상세 화면을 열면 '찾을 수 없는 공고' 안내와 목록 링크가 보인다")
def ac_037_1(page, base):
    page.goto(base + "detail.html?id=JOB-999")
    expect(page.locator("#not-found")).to_be_visible(timeout=TIMEOUT)
    expect(page.locator("#not-found")).to_contain_text("찾을 수 없는 공고")
    expect(page.locator("#not-found a[href='index.html']")).to_have_count(1)
    expect(page.locator("#job-detail")).to_be_hidden()


@ac("AC-008-1", "상세 화면의 저장 버튼을 누르면 '관심 해제'로, 다시 누르면 '관심 공고 저장'으로 바뀐다")
def ac_008_1(page, base):
    page.goto(base + "detail.html?id=JOB-003")
    button = page.locator("#save-toggle")
    expect(button).to_have_text("관심 공고 저장", timeout=TIMEOUT)
    button.click()
    expect(button).to_have_text("관심 해제")
    button.click()
    expect(button).to_have_text("관심 공고 저장")


@ac("AC-009-1", "관심 공고로 저장한 뒤 새로고침해도, 새 탭에서 열어도 저장 상태가 남는다")
def ac_009_1(page, base):
    # Given: JOB-005 가 관심 공고가 아니다 (검사마다 새 브라우저 문맥이라 저장소가 비어 있다)
    page.goto(base + "detail.html?id=JOB-005")
    expect(page.locator("#save-toggle")).to_have_text("관심 공고 저장", timeout=TIMEOUT)
    # When: 저장하고 새로고침한다
    page.click("#save-toggle")
    page.reload()
    # Then: 버튼이 "관심 해제"로 남는다
    expect(page.locator("#save-toggle")).to_have_text("관심 해제", timeout=TIMEOUT)
    # 새 탭에서 연다. sessionStorage 로 잘못 구현하면 새로고침은 통과해도 여기서 실패한다.
    other = page.context.new_page()
    other.goto(base + "saved.html")
    expect(other.locator(".saved-item[data-job-id='JOB-005']")).to_be_visible(timeout=TIMEOUT)


# ---------- 인수 조건: SCR-07 관심 공고 (saved.html) ----------

@ac("AC-038-1", "관심 공고 화면에서 해제하면 그 공고가 목록에서 사라진다")
def ac_038_1(page, base):
    for job_id in ("JOB-001", "JOB-002"):
        save_job(page, base, job_id)
    page.goto(base + "saved.html")
    expect(page.locator(".saved-item")).to_have_count(2, timeout=TIMEOUT)
    page.locator(".saved-item[data-job-id='JOB-001'] .remove-saved").click()
    expect(page.locator(".saved-item")).to_have_count(1)
    expect(page.locator(".saved-item[data-job-id='JOB-002']")).to_be_visible()


@ac("AC-038-2", "관심 공고가 없으면 관심 공고 화면에 빈 상태 안내가 보인다")
def ac_038_2(page, base):
    page.goto(base + "saved.html")
    expect(page.locator("#saved-empty")).to_be_visible(timeout=TIMEOUT)
    expect(page.locator(".saved-item")).to_have_count(0)


# ---------- 인수 조건: SCR-03·04 지원 일정과 등록 (schedule.html) ----------

@ac("AC-010-1", "지원 일정 두 건을 늦은 날짜부터 넣어도 날짜 순으로 보이고 새로고침 뒤에도 남는다")
def ac_010_1(page, base):
    page.goto(base + "schedule.html")
    expect(page.locator("#schedule-job option")).to_have_count(31, timeout=TIMEOUT)
    add_schedule(page, "JOB-002", "면접", "2027-06-10", "2차 면접")
    add_schedule(page, "JOB-001", "서류 마감", "2027-05-20")
    expect(page.locator(".schedule-item")).to_have_count(2, timeout=TIMEOUT)
    dates = page.locator(".schedule-item").evaluate_all("els => els.map(e => e.dataset.date)")
    assert dates == ["2027-05-20", "2027-06-10"], f"날짜 순이 아니다: {dates}"
    page.reload()
    expect(page.locator(".schedule-item")).to_have_count(2, timeout=TIMEOUT)


@ac("AC-031-1", "날짜를 비우고 추가하면 저장되지 않고 오류 문구가 보이며 고른 공고는 남는다")
def ac_031_1(page, base):
    page.goto(base + "schedule.html")
    expect(page.locator("#schedule-job option")).to_have_count(31, timeout=TIMEOUT)
    page.select_option("#schedule-job", "JOB-001")
    page.click("#schedule-form [type=submit]")
    expect(page.locator("#schedule-error")).to_be_visible(timeout=TIMEOUT)
    expect(page.locator("#schedule-error")).not_to_be_empty()
    expect(page.locator(".schedule-item")).to_have_count(0)
    expect(page.locator("#schedule-job")).to_have_value("JOB-001")


@ac("AC-032-1", "삭제 확인에서 취소하면 일정이 남고, 확인하면 사라져 새로고침 뒤에도 없다")
def ac_032_1(page, base):
    page.goto(base + "schedule.html")
    expect(page.locator("#schedule-job option")).to_have_count(31, timeout=TIMEOUT)
    add_schedule(page, "JOB-004", "코딩 테스트", "2027-05-25")
    expect(page.locator(".schedule-item")).to_have_count(1, timeout=TIMEOUT)
    # 확인 창에서 취소한다: 일정이 그대로 있어야 한다
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator(".schedule-item .delete-schedule").first.click()
    expect(page.locator(".schedule-item")).to_have_count(1)
    # 확인 창이 없거나(바로 지움) 확인하면 지워진다. 확인 창이 떴는지도 본다.
    seen = []
    page.once("dialog", lambda dialog: (seen.append(dialog.message), dialog.accept()))
    page.locator(".schedule-item .delete-schedule").first.click()
    expect(page.locator(".schedule-item")).to_have_count(0)
    assert seen, "삭제하기 전에 확인 창이 뜨지 않았다"
    page.reload()
    expect(page.locator("#schedule-empty")).to_be_visible(timeout=TIMEOUT)


# ---------- 인수 조건: 모든 화면 ----------

@ac("AC-039-1", "네 화면을 쓰는 동안 이 사이트 밖으로 나가는 요청이 없다")
def ac_039_1(page, base):
    outside = []
    page.on("request", lambda r: outside.append(r.url) if not r.url.startswith(base) else None)
    for name in ("index.html", "detail.html?id=JOB-006", "saved.html", "schedule.html"):
        page.goto(base + name)
        page.wait_for_load_state("networkidle")
    page.goto(base + "detail.html?id=JOB-006")
    page.click("#save-toggle")
    page.goto(base + "schedule.html")
    expect(page.locator("#schedule-job option")).to_have_count(31, timeout=TIMEOUT)
    add_schedule(page, "JOB-006", "면접", "2027-06-01", "메모")
    page.wait_for_load_state("networkidle")
    assert not outside, f"사이트 밖 요청: {outside}"


@ac("AC-035-1", "폭 320px 화면에서 네 화면 모두 가로 스크롤이 생기지 않는다")
def ac_035_1(page, base):
    page.set_viewport_size({"width": 320, "height": 640})
    for name in ("index.html", "detail.html?id=JOB-001", "saved.html", "schedule.html"):
        page.goto(base + name)
        page.wait_for_load_state("networkidle")
        wide = page.evaluate("document.documentElement.scrollWidth")
        assert wide <= 320, f"{name}: 문서 폭 {wide}px 가 화면 폭 320px 보다 넓다"


# ---------- 실행 ----------

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_server():
    handler = functools.partial(QuietHandler, directory=str(WEB))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    headed = "--headed" in sys.argv
    chosen = [c for c in CHECKS if not args or c[0] in args]
    server, base = start_server()
    print(f"검사 대상: {WEB}")
    print(f"로컬 서버: {base}")
    passed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        for code, title, fn in chosen:
            context = browser.new_context()   # 검사마다 새 문맥: 저장소가 비어 있다
            page = context.new_page()
            try:
                fn(page, base)
                print(f"[통과] {code} {title}")
                passed += 1
            except Exception as error:  # 실패한 까닭의 첫 줄만 보인다
                reason = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
                print(f"[실패] {code} {title}\n         - {reason}")
            finally:
                context.close()
        browser.close()
    server.shutdown()
    print(f"\n브라우저 검사 결과: 통과 {passed} / 실패 {len(chosen) - passed}")
    return 0 if passed == len(chosen) else 1


if __name__ == "__main__":
    sys.exit(main())
