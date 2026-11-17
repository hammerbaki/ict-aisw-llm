"""비식별 검사: 기록에 사람을 알아볼 수 있는 정보가 남았는지 찾는다.

사용법
    python check_pii.py ch05/기록
    python check_pii.py ch05/기록 --names ~/ch05_이름목록.txt

    --names 파일에는 인터뷰한 사람의 실명, 별명, 아이디를 한 줄에 하나씩 적는다.
    이 파일은 저장소 밖(홈 폴더)에 두고 커밋하지 않는다. 수업이 끝나면 지운다.

판정
    실패  전화번호, 이메일, 주민등록번호 형식, 이름 목록의 이름이 있다
    경고  학번으로 보이는 숫자, 학교 이름, SNS 아이디, 상세 주소로 보이는 표현이 있다

    실패가 하나라도 있으면 종료 코드 1이다. 경고는 사람이 읽고 판단한다.
    이 검사는 형식이 뚜렷한 식별자만 찾는다. "우리 과에 한 명뿐인 복학생"처럼
    여러 정보가 합쳐져 사람을 알아보게 되는 경우는 찾지 못한다.
"""
import argparse
import re
import sys
from pathlib import Path

FAIL_PATTERNS = [
    ("전화번호", re.compile(r"(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")),
    ("이메일", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("주민등록번호 형식", re.compile(r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)")),
]
WARN_PATTERNS = [
    ("학번으로 보이는 숫자", re.compile(r"(?<!\d)20\d{6,8}(?!\d)")),
    ("학교 이름", re.compile(r"[가-힣A-Za-z]{2,}(?:대학교|고등학교|폴리텍)")),
    ("SNS 아이디", re.compile(r"(?<![\w.])@[A-Za-z0-9_.]{3,}")),
    ("상세 주소", re.compile(r"[가-힣]+(?:시|구|군)\s+[가-힣0-9]+(?:로|길)\s?\d+")),
]


def scan_text(text, names=()):
    """(실패 목록, 경고 목록). 항목은 (행, 종류, 찾은 문자열)."""
    fails, warns = [], []
    for i, line in enumerate(text.splitlines(), start=1):
        email_spans = []
        for kind, pat in FAIL_PATTERNS:
            for m in pat.finditer(line):
                fails.append((i, kind, m.group(0)))
                if kind == "이메일":
                    email_spans.append(m.span())
        for name in names:
            if name and name in line:
                fails.append((i, "이름 목록의 이름", name))
        for kind, pat in WARN_PATTERNS:
            for m in pat.finditer(line):
                if kind == "SNS 아이디" and any(s <= m.start() < e for s, e in email_spans):
                    continue
                warns.append((i, kind, m.group(0)))
    return fails, warns


def iter_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(x for x in p.rglob("*.md") if not x.name.endswith("_양식.md"))
        elif p.exists():
            yield p


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="기록에 남은 식별 정보를 찾는다")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 폴더")
    parser.add_argument("--names", help="찾을 이름 목록 파일 (저장소 밖에 둔다)")
    args = parser.parse_args(argv)
    names = []
    if args.names:
        names = [n.strip() for n in Path(args.names).read_text(encoding="utf-8").splitlines() if n.strip()]
    files = list(iter_files(args.paths))
    if not files:
        print("[파일 없음] 검사할 .md 파일이 없다")
        return 2
    total_fail = total_warn = 0
    for path in files:
        fails, warns = scan_text(path.read_text(encoding="utf-8"), names)
        for i, kind, found in fails:
            print(f"[실패] {path.name} {i}행: {kind} '{found}'")
        for i, kind, found in warns:
            print(f"[경고] {path.name} {i}행: {kind} '{found}'")
        total_fail += len(fails)
        total_warn += len(warns)
    print(f"\n검사한 파일 {len(files)}개, 이름 목록 {len(names)}개. 실패 {total_fail}, 경고 {total_warn}")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
