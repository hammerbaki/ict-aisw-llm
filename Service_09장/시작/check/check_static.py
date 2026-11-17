"""정적 검사: 웹 폴더의 파일, 공고 자료, HTML 구조, 경로, 금지 사항을 확인한다.

파이썬 표준 라이브러리만 쓴다(설치할 것이 없다). 브라우저를 띄우지 않으므로
자바스크립트가 만드는 화면(카드, 목록)은 확인하지 못한다. 그것은 check_browser.py 가 한다.

    cd ~/llm-service-lab/jobprep/web
    python check/check_static.py              이 폴더(web)를 검사한다
    python check/check_static.py 다른/web      다른 폴더를 검사한다

검사 항목의 번호(S-NN)와 인수 조건 번호(AC-NNN-N)의 관계는 check/README.md 에 있다.
종료 코드: 모두 통과하면 0, 하나라도 실패하면 1.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

WEB = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]

PAGES = ["index.html", "detail.html", "saved.html", "schedule.html"]

# 화면 명세의 「검사용 약속」 식별자 표(index=SCR-01, detail=SCR-02, saved=SCR-07, schedule=SCR-03·04). 구현은 이 id 를 반드시 가져야 한다.
REQUIRED_IDS = {
    "index.html": ["search-input", "filter-category", "filter-region", "result-count",
                   "job-list", "empty-state", "reset-filters"],
    "detail.html": ["job-detail", "job-title", "job-company", "save-toggle", "not-found"],
    "saved.html": ["saved-list", "saved-empty"],
    "schedule.html": ["schedule-form", "schedule-job", "schedule-stage", "schedule-date",
                      "schedule-memo", "schedule-error", "schedule-list", "schedule-empty"],
}

JOB_FIELDS = ["id", "title", "company", "category", "region", "employment_type", "career",
              "education", "posted", "deadline", "summary", "requirements", "preferred"]

# 비밀 정보로 보이는 문자열. 맞으면 실패로 본다(배포 전 점검 도구와 같은 규칙의 일부).
SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "Anthropic API 키 형태"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "GitHub 토큰 형태"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub 세분화 토큰 형태"),
    (re.compile(r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"][^'\"]{6,}['\"]"), "키·비밀번호 대입문"),
]


class PageParser(HTMLParser):
    """한 HTML 파일에서 검사에 필요한 것만 모은다."""

    def __init__(self):
        super().__init__()
        self.html_lang = None
        self.title = ""
        self.in_title = False
        self.has_viewport = False
        self.ids = set()
        self.links = []          # (태그, 속성, 값)
        self.controls = []       # (태그, id, type)
        self.label_for = set()
        self.label_depth = 0
        self.wrapped_controls = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag == "title":
            self.in_title = True
        if tag == "meta" and a.get("name") == "viewport":
            self.has_viewport = True
        if "id" in a:
            self.ids.add(a["id"])
        for attr in ("href", "src"):
            if a.get(attr):
                self.links.append((tag, attr, a[attr]))
        if tag == "label":
            self.label_depth += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            kind = a.get("type", "")
            if kind not in ("hidden", "submit", "button", "reset"):
                self.controls.append((tag, a.get("id"), kind, a.get("aria-label")))
                if self.label_depth and a.get("id"):
                    self.wrapped_controls.add(a["id"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "label" and self.label_depth:
            self.label_depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()


results = []


def check(code, title, problems):
    """problems 가 비어 있으면 통과. 결과를 모아 두고 한 줄로 보인다."""
    ok = not problems
    results.append(ok)
    print(f"[{'통과' if ok else '실패'}] {code} {title}")
    for p in problems[:10]:
        print(f"         - {p}")
    if len(problems) > 10:
        print(f"         - 그 밖에 {len(problems) - 10}건")


def parse(page):
    parser = PageParser()
    parser.feed((WEB / page).read_text(encoding="utf-8"))
    return parser


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(f"검사 대상: {WEB}")

    # S-01 필수 파일
    missing = [p for p in PAGES + ["data/jobs.json"] if not (WEB / p).is_file()]
    check("S-01", "화면 파일 4개와 공고 자료 파일이 있다", [f"없음: {m}" for m in missing])
    if "data/jobs.json" in missing or len(missing) == len(PAGES) + 1:
        print("공고 자료나 화면이 하나도 없어 나머지 검사를 건너뛴다.")
        return 1
    present = [p for p in PAGES if p not in missing]   # 있는 화면만 아래에서 검사한다

    # S-02 공고 자료의 형식
    problems = []
    try:
        data = json.loads((WEB / "data/jobs.json").read_text(encoding="utf-8"))
        jobs = data["jobs"]
        if len(jobs) != 30:
            problems.append(f"공고 수가 30이 아니다: {len(jobs)}")
        ids = [j.get("id") for j in jobs]
        if len(set(ids)) != len(ids):
            problems.append("공고 번호(id)가 겹친다")
        for j in jobs:
            lack = [f for f in JOB_FIELDS if f not in j]
            if lack:
                problems.append(f"{j.get('id')}: 항목 없음 {lack}")
            d = j.get("deadline")
            if d is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d)):
                problems.append(f"{j.get('id')}: 마감일 형식이 YYYY-MM-DD 가 아니다: {d}")
    except (ValueError, KeyError) as error:
        problems.append(f"JSON 을 읽지 못했다: {error}")
    check("S-02", "공고 자료(data/jobs.json)가 30건이고 항목과 날짜 형식이 맞다", problems)

    parsed = {page: parse(page) for page in present}

    # S-03 문서의 기본 구조
    problems = []
    for page, p in parsed.items():
        if p.html_lang != "ko":
            problems.append(f"{page}: <html lang=\"ko\"> 가 아니다")
        if not p.title:
            problems.append(f"{page}: <title> 이 비어 있다")
        if not p.has_viewport:
            problems.append(f"{page}: viewport meta 가 없다")
    check("S-03", "모든 화면에 lang=ko, 제목, viewport 가 있다", problems)

    # S-04 검사용 식별자
    problems = []
    for page, ids in REQUIRED_IDS.items():
        if page not in parsed:
            continue
        lack = [i for i in ids if i not in parsed[page].ids]
        if lack:
            problems.append(f"{page}: id 없음 {lack}")
    check("S-04", "화면 명세의 검사용 식별자(id)가 모두 있다", problems)

    # S-05 상대 경로와 연결 대상
    problems = []
    for page, p in parsed.items():
        for tag, attr, value in p.links:
            if value.startswith(("http://", "https://", "//")):
                problems.append(f"{page}: 외부 주소를 부른다 {attr}={value}")
            elif value.startswith("/"):
                problems.append(f"{page}: / 로 시작하는 경로는 프로젝트 사이트에서 깨진다 {attr}={value}")
            elif not value.startswith(("#", "mailto:", "data:")):
                target = value.split("?")[0].split("#")[0]
                if target and not (WEB / target).exists():
                    problems.append(f"{page}: 연결 대상 파일이 없다 {attr}={value}")
    check("S-05", "경로가 모두 상대 경로이고 연결된 파일이 있다", problems)

    # S-06 레이블 (AC-036-1)
    problems = []
    for page, p in parsed.items():
        for tag, cid, kind, aria in p.controls:
            if aria:
                continue
            if not cid or (cid not in p.label_for and cid not in p.wrapped_controls):
                problems.append(f"{page}: 레이블 없는 입력 <{tag} id={cid}>")
    check("S-06", "모든 입력 요소에 레이블이 있다 (AC-036-1)", problems)

    # S-07 금지 사항: 비밀 정보, innerHTML, 외부 전송 (AC-039-1 보조, REQ-022)
    problems = []
    for path in sorted(WEB.rglob("*")):
        if not path.is_file() or "check" in path.relative_to(WEB).parts:
            continue
        if path.suffix.lower() not in (".html", ".js", ".css", ".json"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(WEB).as_posix()
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{rel}: 비밀 정보로 보이는 문자열 ({label})")
        if path.suffix == ".js":
            if ".innerHTML" in text or "insertAdjacentHTML" in text:
                problems.append(f"{rel}: innerHTML 계열을 쓴다 (명세의 금지 사항)")
            for m in re.finditer(r"fetch\(\s*['\"`]([^'\"`]+)", text):
                if m.group(1).startswith(("http://", "https://", "//", "/")):
                    problems.append(f"{rel}: 외부 또는 절대 경로로 요청한다 fetch({m.group(1)})")
    check("S-07", "비밀 정보, innerHTML, 외부 요청이 없다 (AC-039-1 보조)", problems)

    # S-08 메모 안내 (AC-039-2)
    if "schedule.html" in parsed:
        text = (WEB / "schedule.html").read_text(encoding="utf-8")
        check("S-08", "지원 일정 화면에 개인 정보 입력 금지 안내가 있다 (AC-039-2)",
              [] if "개인 정보" in text else ["schedule.html 에 '개인 정보' 안내 문구가 없다"])

    passed = sum(results)
    print(f"\n정적 검사 결과: 통과 {passed} / 실패 {len(results) - passed}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
