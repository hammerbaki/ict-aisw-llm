"""테스트 동결 검사기: 사람이 정한 테스트가 그대로인지 확인한다.

동결(freeze)은 테스트와 테스트 설정 파일의 지문(SHA-256)을 tests/.baseline.json에 적는 일이다.
검사(check)는 지금의 지문을 동결 기록과 비교해 바뀐 파일(수정, 삭제, 추가)을 알린다.
AI에게 구현을 맡기기 전에 동결하고, AI가 일을 마친 뒤 검사한다.

지켜보는 파일
- tests/ 아래의 모든 파일(.baseline.json, __pycache__, .pyc는 빼고)
- 저장소 루트의 pytest 설정 파일: pytest.ini, pyproject.toml, setup.cfg, tox.ini (있는 것만)
- tests/ 밖에 있는 conftest.py (테스트를 건너뛰게 만드는 데 쓰일 수 있다)
- 이 검사기 파일 자신(tools/test_guard.py)

사용법 (저장소 루트에서)
    python tools/test_guard.py freeze            처음 동결한다. 기록이 있으면 덮어쓰지 않는다
    python tools/test_guard.py freeze --update   사람이 테스트를 바꾸기로 한 뒤 기록을 새로 쓴다
    python tools/test_guard.py check             동결 뒤에 바뀐 것이 있는지 본다

종료 코드: 0 바뀐 것 없음(또는 동결 완료), 1 바뀐 것 있음, 2 사용 오류(기록 없음, tests/ 없음 등)

줄 끝 문자(CRLF와 LF)의 차이는 같은 내용으로 본다. Windows에서 Git이 줄 끝을 바꾼 저장소와
리눅스에서 도는 CI(13장)가 같은 기록을 비교해도 거짓 경보가 나지 않게 하기 위해서다.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

BASELINE = Path("tests") / ".baseline.json"
CONFIG_FILES = ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


def fail(message):
    """사용 오류를 알리고 종료 코드 2로 끝낸다."""
    print(message, file=sys.stderr)
    sys.exit(2)


def fingerprint(path):
    """파일 내용의 SHA-256. 줄 끝 문자는 LF로 맞춘 뒤 계산한다."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def watched_files(root):
    """지켜볼 파일의 목록을 저장소 루트 기준의 상대 경로(슬래시 구분)로 돌려준다."""
    found = set()
    tests = root / "tests"
    for path in tests.rglob("*"):
        if not path.is_file() or path.suffix == ".pyc":
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.resolve() == (root / BASELINE).resolve():
            continue
        found.add(path)
    for name in CONFIG_FILES:
        if (root / name).is_file():
            found.add(root / name)
    for path in root.rglob("conftest.py"):
        if not any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            found.add(path)
    me = Path(__file__).resolve()
    if me.is_relative_to(root.resolve()):
        found.add(me)
    return {path.resolve().relative_to(root.resolve()).as_posix(): fingerprint(path) for path in sorted(found)}


def compare(before, now):
    """두 지문 목록을 비교해 (수정, 삭제, 추가) 세 목록을 돌려준다."""
    changed = sorted(name for name in before.keys() & now.keys() if before[name] != now[name])
    removed = sorted(before.keys() - now.keys())
    added = sorted(now.keys() - before.keys())
    return changed, removed, added


def report(changed, removed, added):
    for label, names in (("수정", changed), ("삭제", removed), ("추가", added)):
        for name in names:
            print(f"  {label}: {name}")


def load_baseline(root):
    path = root / BASELINE
    if not path.exists():
        fail(f"동결 기록이 없다: {BASELINE.as_posix()}. 먼저 freeze를 실행한다.")
    record = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(record, dict) and isinstance(record.get("files"), dict):
        return record["files"]
    return record  # 예전 형식({경로: 해시})도 읽는다


def freeze(root, update):
    path = root / BASELINE
    now = watched_files(root)
    if path.exists() and not update:
        print(f"이미 동결 기록이 있다: {BASELINE.as_posix()}. 덮어쓰지 않는다.", file=sys.stderr)
        print("테스트를 바꾸기로 사람이 정했다면 --update를 붙여 다시 실행한다.", file=sys.stderr)
        return 2
    if path.exists():
        changed, removed, added = compare(load_baseline(root), now)
        if not (changed or removed or added):
            print("바뀐 것이 없어 동결 기록을 그대로 둔다.")
            return 0
        print("동결 기록을 고친다. 바뀐 파일:")
        report(changed, removed, added)
    record = {
        "version": 1,
        "frozen_at": datetime.now().isoformat(timespec="seconds"),
        "files": now,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")  # Windows에서도 LF로 쓴다
    tests_count = sum(1 for name in now if name.startswith("tests/"))
    print(f"동결 완료: 파일 {len(now)}개 (tests/ {tests_count}개, 설정과 검사기 {len(now) - tests_count}개)")
    return 0


def check(root):
    before = load_baseline(root)
    now = watched_files(root)
    changed, removed, added = compare(before, now)
    if changed or removed or added:
        print("TEST_CHANGED: 동결한 뒤 바뀐 파일이 있다")
        report(changed, removed, added)
        return 1
    print(f"TEST_UNCHANGED ({BASELINE.as_posix()} 기준, 파일 {len(now)}개)")
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="테스트 동결 검사기")
    parser.add_argument("action", choices=["freeze", "check"])
    parser.add_argument("--update", action="store_true", help="freeze에서 기존 동결 기록을 새로 쓴다")
    parser.add_argument("--root", default=".", help="저장소 루트(기본값: 지금 폴더)")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not (root / "tests").is_dir():
        fail(f"tests/ 폴더가 없다: {root}. 저장소 루트에서 실행한다.")
    if args.action == "freeze":
        sys.exit(freeze(root, args.update))
    sys.exit(check(root))


if __name__ == "__main__":
    main()
