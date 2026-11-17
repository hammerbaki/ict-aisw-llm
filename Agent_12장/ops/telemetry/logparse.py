"""운영 기록 읽기: `날짜 시각 수준 기록기 키=값…` 형식의 줄을 dict로 바꾼다.

사용법
    python -m ops.telemetry.logparse logs/llm.log             앞의 다섯 줄을 JSON Lines로 보인다
    python -m ops.telemetry.logparse logs/llm.log --all > x.jsonl   모두 JSON Lines로 바꾼다

형식은 logs/README.md에 있다. 값에 빈칸이 있으면 큰따옴표로 감싸여 있다.
"""

import json
import re
import shlex
import sys
from pathlib import Path

HEAD = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (\w+) (\S+)\s?(.*)$")
NUMBER = re.compile(r"^-?\d+$")


def parse_line(line):
    """한 줄을 {ts, level, logger, 키…}로 바꾼다. 형식이 맞지 않으면 None."""
    match = HEAD.match(line.strip())
    if not match:
        return None
    day, clock, level, logger, rest = match.groups()
    record = {"ts": f"{day}T{clock}", "level": level, "logger": logger}
    try:
        parts = shlex.split(rest)
    except ValueError:          # 따옴표가 짝이 맞지 않는 줄
        return None
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        record[key] = int(value) if NUMBER.match(value) else value
    return record


def read_log(path):
    """기록 파일의 모든 줄을 읽는다. 읽지 못한 줄의 수도 함께 돌려준다."""
    records, bad = [], 0
    path = Path(path)
    if not path.exists():
        return records, bad
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = parse_line(line)
        if record is None:
            bad += 1
        else:
            records.append(record)
    return records, bad


def read_jsonl(paths):
    """JSON Lines 파일들을 읽어 줄마다 dict로 돌려준다."""
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    records, bad = read_log(argv[0])
    shown = records if "--all" in argv else records[:5]
    for record in shown:
        print(json.dumps(record, ensure_ascii=False))
    if "--all" not in argv:
        print(f"(전체 {len(records)}줄, 읽지 못한 줄 {bad}개)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
