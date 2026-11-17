"""기록 속 개인 정보와 비밀 정보 점검: 기록 파일에서 전자우편, 휴대전화 번호, 주민등록번호 꼴, API 키 꼴의 문자열을 찾는다.

사용법
    python -m ops.telemetry.pii_scan logs evals/runs ops

종료 코드: 0 발견 없음, 1 발견 있음(발견한 값은 가려서 보인다)
이 검사는 정규식에 걸리는 꼴만 찾는다. 이름, 주소, 질문 원문에 섞인 개인 사정처럼 꼴이 없는 정보는 찾지 못한다.
"""

import re
import sys
from pathlib import Path

PATTERNS = {
    "전자우편": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "휴대전화": re.compile(r"01[016789][- ]?\d{3,4}[- ]?\d{4}"),
    "주민등록번호 꼴": re.compile(r"\d{6}-[1-4]\d{6}"),
    "API 키 꼴": re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
}
SUFFIXES = {".log", ".jsonl", ".json", ".md", ".txt", ".csv"}


def mask(value):
    """앞 세 글자만 남기고 가린다."""
    return value[:3] + "*" * max(0, len(value) - 3)


def scan_text(text):
    """글에서 찾은 (종류, 줄 번호, 가린 값)의 목록을 돌려준다."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                found.append((kind, number, mask(match.group(0))))
    return found


def scan_paths(paths):
    results = []
    for root in paths:
        root = Path(root)
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix in SUFFIXES)
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            results += [(path.as_posix(), *item) for item in scan_text(text)]
    return results


def main(argv=None):
    paths = (sys.argv[1:] if argv is None else argv) or ["logs"]
    results = scan_paths(paths)
    for path, kind, number, value in results:
        print(f"{path}:{number} {kind} {value}")
    print(f"점검한 경로: {', '.join(paths)} · 발견 {len(results)}건")
    return 1 if results else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
