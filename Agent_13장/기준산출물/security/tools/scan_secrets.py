"""저장소에서 비밀 정보(키, 토큰, 개인 키)의 모양을 찾는 검사기이다. 11장 실습용.

기본으로는 「커밋될 수 있는 파일」만 본다: git이 추적하는 파일과, 추적하지 않지만 .gitignore에 걸리지 않은 파일.
.gitignore로 빠진 파일(.env, secrets/)은 --include-ignored를 주면 「무시됨」으로 따로 보여 준다.
--history를 주면 모든 브랜치의 커밋 기록에서 더해진 줄(git log -p의 + 줄)도 본다.
비밀은 앞 8자만 남기고 가려서 출력한다.

종료 코드: 커밋될 수 있는 곳(또는 기록)에서 찾으면 1, 없으면 0. 무시된 파일의 발견은 종료 코드에 넣지 않는다.

예외: 줄에 `secret-scan: allow`를 적거나, security/allowlist.txt에 「경로」 또는 「경로:종류」를 한 줄에
하나씩 적는다(13장 키트의 예외 목록과 같은 자리). 일부러 넣은 가짜 값에만 쓰고, 까닭을 위 줄에 주석으로 남긴다.

쓰는 법 (저장소 폴더에서)
    python security/tools/scan_secrets.py          # security/scan_secrets.py도 같은 검사를 부른다(13장 CI용)
    python security/tools/scan_secrets.py --include-ignored
    python security/tools/scan_secrets.py --history
    python security/tools/scan_secrets.py 경로1 경로2      # 지정한 파일만
"""

import argparse
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secret_patterns import find_secrets  # noqa: E402

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
MAX_BYTES = 1_000_000  # 이보다 큰 파일은 건너뛴다(기록 견본 등)


def load_allowlist(root):
    """security/allowlist.txt의 (경로 패턴, 종류 또는 None) 목록."""
    path = root / "security" / "allowlist.txt"
    entries = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                pattern, _, kind = line.partition(":")
                entries.append((pattern.strip(), kind.strip() or None))
    return entries


def allowed(rel, kind, entries):
    return any(fnmatch(rel, pattern) and (k is None or k == kind) for pattern, k in entries)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout


def committable_files(root):
    """추적 중이거나, 추적하지 않지만 무시되지 않은 파일 목록."""
    out = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({p for p in out.split("\0") if p})


def ignored_files(root):
    out = git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard")
    files = []
    for p in out.split("\0"):
        if p and not set(Path(p).parts) & SKIP_DIRS:
            files.append(p)
    return sorted(files)


def read_text(path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None  # 이진 파일
    return data.decode("utf-8", errors="replace")


def scan_files(root, rel_paths):
    findings = []
    for rel in rel_paths:
        text = read_text(root / rel)
        if text is None:
            continue
        for lineno, kind, shown in find_secrets(text):
            findings.append((rel, lineno, kind, shown))
    return findings


def scan_history(root):
    """모든 브랜치 기록에서 더해진 줄을 본다. (커밋, 파일, 종류, 가린 값)을 돌려준다."""
    log = git(root, "log", "--all", "-p", "--no-color", "--unified=0", "--format=commit %h")
    findings, commit, current = [], "?", "?"
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1]
        elif line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for _, kind, shown in find_secrets(line[1:]):
                findings.append((commit, current, kind, shown))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description="저장소의 비밀 정보 모양 검사(학습용)")
    parser.add_argument("paths", nargs="*", help="검사할 파일. 주지 않으면 커밋될 수 있는 파일 전체")
    parser.add_argument("--root", default=".", help="저장소 폴더(기본: 현재 폴더)")
    parser.add_argument("--include-ignored", action="store_true", help=".gitignore로 빠진 파일도 보여 준다")
    parser.add_argument("--history", action="store_true", help="커밋 기록의 더해진 줄도 본다")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.paths:
        targets = args.paths
    else:
        targets = [p for p in committable_files(root) if not set(Path(p).parts) & SKIP_DIRS]
    entries = load_allowlist(root)
    findings = [f for f in scan_files(root, targets) if not allowed(f[0], f[2], entries)]
    print(f"검사한 파일: {len(targets)}개")
    for rel, lineno, kind, shown in findings:
        print(f"  발견  {rel}:{lineno}  {kind}  {shown}")

    if args.include_ignored and not args.paths:
        for rel, lineno, kind, shown in scan_files(root, ignored_files(root)):
            print(f"  무시됨(커밋되지 않음)  {rel}:{lineno}  {kind}  {shown}")

    history = []
    if args.history:
        history = [h for h in scan_history(root) if not allowed(h[1], h[2], entries)]
        for commit, rel, kind, shown in history:
            print(f"  기록  {commit} {rel}  {kind}  {shown}")

    total = len(findings) + len(history)
    if total:
        print(f"결과: 비밀로 보이는 값 {total}건. 키를 지우는 것만으로는 부족하다. 실제 키라면 먼저 폐기하고 새로 발급한다.")
        return 1
    print("결과: 커밋될 수 있는 곳에서 비밀로 보이는 값을 찾지 못하였다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
