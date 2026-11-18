"""인터뷰와 논의의 기록 파일의 형식을 읽는 공용 모듈.

기록 파일은 `## 기록` 제목 아래에 한 줄에 한 발화(또는 관찰)를 둔다.

    L12 A: 날짜를 하나씩 바꿔 가며 빈 시간을 찾았다.

- `L12`  줄 번호. 1부터 차례로 늘어나며, 한 번 붙인 번호는 바꾸지 않는다.
- `A`    화자 표시. Q(진행자의 질문), A(참여자의 말), 관찰(진행자가 본 행동),
         메모(진행자의 해석). 근거로 인용할 수 있는 것은 A와 관찰이다.
"""
import re
from pathlib import Path

SPEAKERS = ("Q", "A", "관찰", "메모")
EVIDENCE_SPEAKERS = ("A", "관찰")
SECTION_TITLE = "기록"

NUMBERED = re.compile(r"^L(\d+)\s+(Q|A|관찰|메모)\s*[:：]\s?(.*)$")
UNNUMBERED = re.compile(r"^(Q|A|관찰|메모)\s*[:：]\s?(.*)$")
HEADING2 = re.compile(r"^##\s+(.*?)\s*$")


class RecordFormatError(Exception):
    """기록 파일의 형식이 규칙에 맞지 않을 때."""


def record_section(lines):
    """`## 기록` 제목 다음 줄부터 다음 `## ` 제목 전까지의 (파일 줄 번호, 내용) 목록."""
    inside = False
    out = []
    for i, line in enumerate(lines, start=1):
        m = HEADING2.match(line)
        if m:
            inside = m.group(1).strip() == SECTION_TITLE
            continue
        if inside:
            out.append((i, line))
    return out


def load_record(path):
    """기록 파일을 읽어 {줄 번호: (화자, 내용)}을 돌려준다.

    번호가 겹치거나 줄어들면 RecordFormatError를 낸다.
    """
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    titles = [m.group(1).strip() for m in map(HEADING2.match, lines) if m]
    if SECTION_TITLE not in titles:
        raise RecordFormatError(f"{path.name}: '## {SECTION_TITLE}' 제목이 없다")
    section = record_section(lines)
    entries = {}
    last = 0
    for file_line, text in section:
        m = NUMBERED.match(text.strip())
        if not m:
            continue
        number = int(m.group(1))
        if number in entries:
            raise RecordFormatError(f"{path.name} {file_line}행: L{number}이 두 번 나온다")
        if number < last:
            raise RecordFormatError(f"{path.name} {file_line}행: L{number}이 앞 번호 L{last}보다 작다")
        entries[number] = (m.group(2), m.group(3).strip())
        last = number
    return entries


def load_records(directory):
    """폴더 안의 .md 기록 파일을 모두 읽는다. {기록 이름: entries}"""
    directory = Path(directory)
    records = {}
    for path in sorted(directory.glob("*.md")):
        if path.name.endswith("_양식.md"):
            continue
        records[path.stem] = load_record(path)
    return records
