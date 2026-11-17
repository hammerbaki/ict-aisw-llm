"""API 키가 저장소와 브라우저 코드에 없는지 검사한다. 저장소 폴더(또는 jobprep 폴더)에서 실행한다.

    python tools/check_secrets.py            현재 폴더를 검사
    python tools/check_secrets.py <폴더>     지정한 폴더를 검사

검사하는 것
  1. 키 모양의 문자열(sk-ant-...)이 파일에 있는가          → 어디에도 있으면 안 된다
  2. .env 밖의 파일에서 ANTHROPIC_API_KEY 뒤에 값이 적혀 있는가 → .env.example은 값이 비어 있어야 한다
  3. 웹(web/) 코드가 Claude API를 직접 부르는가            → 브라우저는 우리 서버만 불러야 한다
  4. .env 가 git에 올라가 있는가, .gitignore 에 .env 가 있는가

찾은 값은 앞 몇 글자만 보이고 나머지는 가린다. 결과는 마지막 줄 KEY_CHECK_OK 또는 KEY_CHECK_FAIL.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

KEY = re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}")
ASSIGN = re.compile(r"ANTHROPIC_API_KEY\s*[=:]\s*['\"]?([^\s'\"#]+)")
BROWSER_CALL = re.compile(r"api\.anthropic\.com|x-api-key|anthropic-version", re.IGNORECASE)
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", "results"}
TEXT_SUFFIX = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".json", ".md", ".txt", ".toml", ".ini",
               ".cfg", ".yml", ".yaml", ".sh", ".env", ".example", ""}
PLACEHOLDERS = {"", "여기에_키", "your-key-here", "<키>"}


def mask(value: str) -> str:
    return value[:7] + "…(가림)"


def files_to_scan(root: Path) -> list[Path]:
    out = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and (path.suffix in TEXT_SUFFIX or path.name.startswith(".env")):
            out.append(path)
    return out


def git_tracked(root: Path, name: str) -> bool:
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", name], cwd=root,
                           capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return r.returncode == 0


def inside_git(root: Path) -> bool:
    try:
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root,
                           capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return r.returncode == 0 and r.stdout.strip() == "true"


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for path in files_to_scan(root):
        rel = path.relative_to(root).as_posix()
        is_dotenv = path.name == ".env"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for no, line in enumerate(lines, 1):
            m = KEY.search(line)
            if m and not is_dotenv:
                problems.append(f"{rel}:{no} 키 모양의 문자열 {mask(m.group(0))}")
            a = ASSIGN.search(line)
            if a and not is_dotenv and a.group(1) not in PLACEHOLDERS and not a.group(1).startswith("$"):
                problems.append(f"{rel}:{no} ANTHROPIC_API_KEY에 값이 적혀 있음 {mask(a.group(1))}")
            if rel.startswith("web/") and BROWSER_CALL.search(line):
                problems.append(f"{rel}:{no} 브라우저 코드가 Claude API를 직접 부름")
    if inside_git(root):
        if (root / ".env").exists() and git_tracked(root, ".env"):
            problems.append(".env 가 git에 올라가 있음 (git rm --cached .env 로 내리고 키를 폐기한다)")
        elif not git_ignored(root, ".env"):
            problems.append(".env 가 .gitignore 로 제외되지 않음 (.gitignore 에 .env 한 줄을 더한다)")
    return problems


def git_ignored(root: Path, name: str) -> bool:
    """상위 폴더의 .gitignore까지 포함해 git이 그 이름을 무시하는지 git에게 직접 묻는다."""
    r = subprocess.run(["git", "check-ignore", "-q", name], cwd=root, capture_output=True, text=True)
    return r.returncode == 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0] if argv else ".").resolve()
    problems = check(root)
    for p in problems:
        print("문제:", p)
    print(f"검사한 폴더: {root.name}  문제 {len(problems)}건")
    print("KEY_CHECK_OK" if not problems else "KEY_CHECK_FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
