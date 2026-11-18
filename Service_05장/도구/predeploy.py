"""배포 전 점검: 공개할 폴더를 읽어 공개되면 안 되는 것을 찾는다. (「LLM 서비스 개발」 5장 키트)

    python predeploy.py ~/jobs-board
    python predeploy.py ch05/web --deny busino --deny basicAddr

하는 일
  1. 폴더의 파일을 공개될 것과 아닌 것으로 나누어 보인다. 점(.)으로 시작하는 파일과 폴더
     (.git 등)는 GitHub Pages가 내보내지 않거나 저장소의 관리 파일이므로 건너뛴다.
     웹에 쓰지 않는 확장자(.py, .md, .xml, .env 등)가 있으면 멈춘다.
  2. 환경 변수 WORK24_KEY가 있으면 그 값이 어느 파일에든 들어 있는지 찾는다.
     API 키, 토큰처럼 보이는 문자열과 휴대전화 번호, 주민등록번호, 전자우편 주소의 꼴도 찾는다.
  3. 자료 파일(data/*.json)의 공고마다 어떤 항목이 있는지 보이고, --deny로 준 항목
     (기본: busino 사업자등록번호)이 있으면 멈춘다.
  4. / 로 시작하는 경로가 있으면 알린다. 프로젝트 사이트(아이디.github.io/저장소/)에서 깨진다.

이 도구는 정해진 꼴만 찾는다. 통과가 안전을 보증하지 않는다. 목록과 내용은 사람이 한 번 더 읽는다.
파일을 고치거나 복사하지 않는다. 종료 코드: 문제가 없으면 0, 멈추면 1, 폴더가 없으면 2.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

WEB = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".ico",
       ".woff", ".woff2", ".txt"}
TEXT = {".html", ".css", ".js", ".json", ".svg", ".txt"}
SECRETS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "Anthropic API 키 꼴"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "GitHub 토큰 꼴"),
    (re.compile(r"(?i)auth_?key=[A-Za-z0-9\-]{8,}"), "주소에 붙은 인증키(authKey=)"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{6,}['\"]"), "키·비밀번호 대입문"),
]
PERSONAL = [
    (re.compile(r"01[016789]-?\d{3,4}-?\d{4}"), "휴대전화 번호 꼴"),
    (re.compile(r"\d{6}-[1-4]\d{6}"), "주민등록번호 꼴"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "전자우편 주소 꼴"),
]
ABS_PATH = re.compile(r"""(?:src|href)\s*=\s*["']/(?!/)|fetch\(\s*["'`]/(?!/)""")


def collect(root):
    public, skipped = [], []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            skipped.append(rel)
        else:
            public.append(rel)
    return public, skipped


def fields_of(data):
    jobs = data.get("jobs") if isinstance(data, dict) else data
    found = set()
    for job in jobs if isinstance(jobs, list) else []:
        if isinstance(job, dict):
            found.update(job)
    return found


def check(root, deny, key):
    stops, warns, info = [], [], []
    public, skipped = collect(root)
    for rel in public:
        path = root / rel
        name = rel.as_posix()
        suffix = path.suffix.lower()
        if suffix not in WEB:
            stops.append(f"{name}: 웹에 쓰지 않는 파일이다 ({suffix or '확장자 없음'}). 공개 폴더에서 뺀다")
            continue
        if suffix not in TEXT:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if key and key in text:
            stops.append(f"{name}: WORK24_KEY의 값이 들어 있다")
        for pattern, label in SECRETS + PERSONAL:
            m = pattern.search(text)
            if m:
                stops.append(f"{name}: {label}으로 보인다 ({m.group(0)[:6]}…)")
        if suffix in (".html", ".js") and ABS_PATH.search(text):
            warns.append(f"{name}: / 로 시작하는 경로가 있다. 프로젝트 사이트에서 깨진다")
        if suffix == ".json" and rel.parts[0] == "data":
            try:
                found = fields_of(json.loads(text))
            except json.JSONDecodeError as e:
                stops.append(f"{name}: JSON으로 읽지 못했다 ({e.msg})")
                continue
            info.append(f"{name}의 항목: {', '.join(sorted(found)) or '(공고 없음)'}")
            for f in sorted(found & set(deny)):
                stops.append(f"{name}: 공개하지 않기로 한 항목 {f}가 있다")
    return public, skipped, stops, warns, info


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="배포 전 점검")
    ap.add_argument("folder", help="공개할 폴더 (예: ~/jobs-board)")
    ap.add_argument("--deny", action="append", help="자료 파일에 있으면 안 되는 항목. 여러 번 줄 수 있다. 기본: busino")
    a = ap.parse_args(argv)
    root = Path(a.folder).expanduser()
    if not root.is_dir():
        print(f"폴더가 없다: {a.folder}")
        return 2
    key = os.environ.get("WORK24_KEY", "").strip()
    public, skipped, stops, warns, info = check(root, a.deny or ["busino"], key)
    print(f"점검한 폴더: {a.folder}")
    print("WORK24_KEY: " + ("값을 읽어 찾았다" if key else "환경 변수가 없어 찾지 않았다 (source ~/work24.env 뒤 다시 실행)"))
    print(f"\n공개될 파일 {len(public)}개")
    for rel in public:
        print(f"  + {rel.as_posix()}")
    print(f"건너뛴 파일 {len(skipped)}개 (점으로 시작하는 이름)")
    for line in info:
        print(f"\n{line}")
    if warns:
        print("\n주의")
        for w in warns:
            print(f"  ! {w}")
    if stops:
        print("\n멈춤: 아래를 고친 뒤 다시 실행한다")
        for s in stops:
            print(f"  x {s}")
        return 1
    print(f"\nPREDEPLOY_OK {len(public)} files")
    print("자동 점검은 정해진 꼴만 찾는다. 위 목록과 항목을 직접 읽고 푸시한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
