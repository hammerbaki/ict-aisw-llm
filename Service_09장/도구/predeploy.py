"""배포 전 점검: 공개할 파일만 골라 공개 폴더(_site)를 만들고, 비밀 정보와 개인 정보를 찾는다.

저장소 맨 위(llm-service-lab)에서 실행한다. GitHub Actions 워크플로도 같은 명령을 쓴다.

    python jobprep/tools/predeploy.py                       jobprep/web → _site
    python jobprep/tools/predeploy.py --src jobprep/web --out _site

하는 일
  1. 원본 폴더에서 공개할 파일만 고른다. check/ 폴더, 점(.)으로 시작하는 파일과 폴더,
     정해진 확장자 밖의 파일은 빼고, 뺀 목록을 보인다.
  2. 고른 파일에서 비밀 정보(API 키, 토큰, 비밀번호 대입문)와 개인 정보(휴대전화 번호,
     주민등록번호, 전자우편 주소)로 보이는 문자열을 찾는다. 하나라도 있으면 멈춘다.
  3. 파일 크기와 / 로 시작하는 경로를 확인한다.
  4. 문제가 없으면 공개 폴더를 새로 만들고 파일을 복사한다.

이 도구는 정해진 형태만 찾는다. 통과가 안전을 보증하지 않는다. 공개 폴더의 목록과
내용은 사람이 한 번 더 읽는다.
종료 코드: 문제가 없으면 0, 멈추면 1.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ALLOWED = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".svg", ".webp",
           ".gif", ".ico", ".woff", ".woff2", ".txt"}
TEXT = {".html", ".css", ".js", ".json", ".svg", ".txt"}
SKIP_DIRS = {"check", "node_modules", "__pycache__"}
MAX_FILE = 5 * 1024 * 1024        # 파일 하나 5MB
MAX_TOTAL = 50 * 1024 * 1024      # 전체 50MB (GitHub Pages 한도 1GB 보다 훨씬 작게 둔다)
MARKER = ".made-by-predeploy"     # 이 도구가 만든 폴더라는 표시. 점 파일이라 공개되지 않는다

SECRETS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "Anthropic API 키 형태"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "API 키 형태(sk-)"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "GitHub 토큰 형태"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub 세분화 토큰 형태"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS 액세스 키 형태"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "개인 키"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
     "키·비밀번호 대입문"),
]
PERSONAL = [
    (re.compile(r"01[016789]-?\d{3,4}-?\d{4}"), "휴대전화 번호 형태"),
    (re.compile(r"\d{6}-[1-4]\d{6}"), "주민등록번호 형태"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "전자우편 주소 형태"),
]
ABS_PATH = re.compile(r"""(?:src|href)\s*=\s*["']/(?!/)|fetch\(\s*["'`]/(?!/)""")


def collect(src):
    keep, skipped = [], []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        parts = rel.parts
        if any(p.startswith(".") for p in parts):
            skipped.append((rel, "점으로 시작하는 이름"))
        elif any(p in SKIP_DIRS for p in parts[:-1]):
            skipped.append((rel, "공개하지 않는 폴더"))
        elif path.is_symlink():
            skipped.append((rel, "심볼릭 링크"))
        elif path.suffix.lower() not in ALLOWED:
            skipped.append((rel, f"공개하지 않는 확장자 {path.suffix or '(없음)'}"))
        else:
            keep.append(rel)
    return keep, skipped


def scan(src, files):
    stops, warns = [], []
    total = 0
    for rel in files:
        path = src / rel
        rel = rel.as_posix()
        size = path.stat().st_size
        total += size
        if size > MAX_FILE:
            stops.append(f"{rel}: 파일이 너무 크다 ({size // 1024} KB)")
        if path.suffix.lower() not in TEXT:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, label in SECRETS:
            if pattern.search(text):
                stops.append(f"{rel}: 비밀 정보로 보인다 ({label})")
        for pattern, label in PERSONAL:
            m = pattern.search(text)
            if m:
                stops.append(f"{rel}: 개인 정보로 보인다 ({label}: {m.group(0)[:4]}…)")
        if path.suffix.lower() in (".html", ".js") and ABS_PATH.search(text):
            warns.append(f"{rel}: / 로 시작하는 경로가 있다. 프로젝트 사이트(…github.io/저장소/)에서 깨진다")
    if total > MAX_TOTAL:
        stops.append(f"전체 크기가 너무 크다 ({total // 1024} KB)")
    return stops, warns, total


def check_repo(root):
    """저장소 수준의 확인: .env 가 .gitignore 에 있는가, 공개 폴더가 커밋되지 않게 되어 있는가."""
    warns = []
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    if ".env" not in text:
        warns.append(".gitignore 에 .env 가 없다. 10장에서 API 키를 쓰기 전에 넣는다")
    if "_site" not in text:
        warns.append(".gitignore 에 _site/ 가 없다. 공개 폴더는 만들어 쓰는 것이므로 커밋하지 않는다")
    return warns


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="배포 전 점검과 공개 폴더 만들기")
    ap.add_argument("--src", default="jobprep/web", help="원본 폴더 (기본: jobprep/web)")
    ap.add_argument("--out", default="_site", help="공개 폴더 (기본: _site)")
    a = ap.parse_args()

    root = Path.cwd()
    src, out = (root / a.src).resolve(), (root / a.out).resolve()
    if not (src / "index.html").is_file():
        print(f"멈춤: {a.src}/index.html 이 없다. 저장소 맨 위에서 실행했는지 확인한다.")
        return 1
    if out.exists() and not (out / MARKER).exists():
        print(f"멈춤: {a.out} 가 이미 있고 이 도구가 만든 폴더가 아니다. 이름을 바꾸어 보관한 뒤 다시 실행한다.")
        return 1

    files, skipped = collect(src)
    stops, warns, total = scan(src, files)
    warns += check_repo(root)

    print(f"원본: {a.src}  →  공개 폴더: {a.out}")
    print(f"\n공개할 파일 {len(files)}개 ({total // 1024} KB)")
    for rel in files:
        print(f"  + {rel.as_posix()}")
    print(f"\n뺀 파일 {len(skipped)}개")
    for rel, why in skipped:
        print(f"  - {rel.as_posix()}  ({why})")
    if warns:
        print("\n주의")
        for w in warns:
            print(f"  ! {w}")
    if stops:
        print("\n멈춤: 아래를 고친 뒤 다시 실행한다")
        for s in stops:
            print(f"  x {s}")
        return 1

    if out.exists():
        shutil.rmtree(out)
    for rel in files:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
    (out / MARKER).write_text("predeploy.py 가 만든 공개 폴더\n", encoding="utf-8")
    print(f"\nPREDEPLOY_OK {len(files)} files -> {a.out}")
    print("자동 점검은 정해진 형태만 찾는다. 위 목록과 파일 내용을 직접 읽고 배포한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
