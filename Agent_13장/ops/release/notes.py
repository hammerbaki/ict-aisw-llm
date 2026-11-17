"""CHANGELOG.md에서 판 하나의 절을 뽑아 표준 출력으로 낸다 (13장).

CHANGELOG.md는 Keep a Changelog 1.1.0의 형식을 따른다:
    ## [1.0.1] - 2027-12-08
    ### Fixed
    - ...

쓰는 법 (저장소 폴더에서)
    python ops/release/notes.py v1.0.1        v를 붙여도 되고 빼도 된다
    python ops/release/notes.py --check v1.0.1  절이 있고 비어 있지 않은지만 본다
종료 코드: 0 찾음, 1 그 판의 절이 없거나 비어 있음, 2 판 이름이 시맨틱 버저닝 형식이 아님
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")
HEADER = re.compile(r"^## \[(?P<version>[^\]]+)\](?: - (?P<date>\d{4}-\d{2}-\d{2}))?\s*$")


def section(text, version):
    """버전의 절 본문(머리 줄 다음부터 다음 ## 절 앞까지)을 돌려준다. 없으면 None이다."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        found = HEADER.match(line)
        if found and start is None and found.group("version") == version:
            start = index + 1
        elif start is not None and line.startswith("## "):
            return "\n".join(lines[start:index]).strip()
    return "\n".join(lines[start:]).strip() if start is not None else None


def main(argv=None):
    parser = argparse.ArgumentParser(description="CHANGELOG.md에서 릴리스 본문 뽑기")
    parser.add_argument("tag", help="판 태그(v1.0.1 또는 1.0.1)")
    parser.add_argument("--check", action="store_true", help="본문을 출력하지 않고 확인만 한다")
    args = parser.parse_args(argv)

    if not SEMVER.match(args.tag):
        print(f"시맨틱 버저닝 형식이 아니다: {args.tag}", file=sys.stderr)
        return 2
    version = args.tag[1:] if args.tag.startswith("v") else args.tag
    if not CHANGELOG.is_file():
        print("CHANGELOG.md가 없다", file=sys.stderr)
        return 1
    body = section(CHANGELOG.read_text(encoding="utf-8"), version)
    if not body:
        print(f"CHANGELOG.md에 [{version}] 절이 없거나 비어 있다", file=sys.stderr)
        return 1
    if args.check:
        print(f"[{version}] 절 확인: {len(body.splitlines())}줄")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
