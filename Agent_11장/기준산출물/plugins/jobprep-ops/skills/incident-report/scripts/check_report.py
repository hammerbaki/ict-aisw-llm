#!/usr/bin/env python3
"""장애 보고서가 정해진 서식(references/보고서서식.md)을 지켰는지 검사한다.

내용이 맞는지(원인 판단이 옳은지)는 사람이 본다. 이 스크립트는 서식만 기계로 판정한다.
스킬은 보고서를 저장한 뒤 이 스크립트를 실행하고, 실패하면 고쳐서 다시 실행한다.

사용:
    python check_report.py docs/운영/장애보고/2027-09-08.md

종료 코드: 0 통과, 1 서식 위반(위반 목록을 출력), 2 파일 없음.
"""
import re
import sys
from pathlib import Path

TITLE_RE = re.compile(r"^# 장애 보고서: (\d{4}-\d{2}-\d{2}) \S")
SEVERITY_RE = re.compile(r"^- 심각도: (SEV[123])\b", re.M)
SECTIONS = ["## 1. 요약", "## 2. 영향", "## 3. 경과", "## 4. 원인", "## 5. 조치와 재발 방지", "## 6. 근거 기록"]
TIME_RE = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")
LOG_REF_RE = re.compile(r"logs/[\w.-]+\.log")
LEFTOVER = ["{{", "}}", "TODO"]   # 서식의 자리 표시는 {{이름}} 꼴이다


def section_body(lines, title):
    """제목 줄 다음부터 다음 ## 제목 전까지의 줄."""
    start = lines.index(title) + 1
    body = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def table_rows(body):
    """마크다운 표의 데이터 행(머리 행과 구분 행 제외)을 칸 목록으로."""
    rows = [l.strip() for l in body if l.strip().startswith("|")]
    data = [r for r in rows[2:]] if len(rows) >= 2 else []
    return [[c.strip() for c in r.strip("|").split("|")] for r in data]


def check(text):
    """위반 목록을 돌려준다. 빈 목록이면 통과."""
    problems = []
    lines = [l.rstrip() for l in text.splitlines()]
    if not lines or not TITLE_RE.match(lines[0]):
        problems.append("첫 줄이 '# 장애 보고서: YYYY-MM-DD 제목' 형식이 아니다")
    if not SEVERITY_RE.search(text):
        problems.append("'- 심각도: SEV1|SEV2|SEV3' 줄이 없다")

    positions = []
    for title in SECTIONS:
        if title in lines:
            positions.append(lines.index(title))
        else:
            problems.append(f"절이 없다: {title}")
    if len(positions) == len(SECTIONS) and positions != sorted(positions):
        problems.append("절의 순서가 서식과 다르다")

    if "## 3. 경과" in lines:
        rows = table_rows(section_body(lines, "## 3. 경과"))
        if len(rows) < 2:
            problems.append("경과 표의 행이 2개보다 적다")
        for i, row in enumerate(rows, 1):
            if not TIME_RE.match(row[0]):
                problems.append(f"경과 표 {i}행: 첫 칸이 시각(HH:MM 또는 HH:MM:SS)이 아니다")
            if not LOG_REF_RE.search(row[-1]):
                problems.append(f"경과 표 {i}행: 마지막 칸(근거)에 logs/파일.log 경로가 없다")

    if "## 4. 원인" in lines:
        cause = "\n".join(section_body(lines, "## 4. 원인"))
        if not (LOG_REF_RE.search(cause) or "확인 필요" in cause):
            problems.append("원인 절에 근거 기록 경로도 '확인 필요' 표시도 없다")

    if "## 6. 근거 기록" in lines:
        evidence = "\n".join(section_body(lines, "## 6. 근거 기록"))
        if not LOG_REF_RE.search(evidence):
            problems.append("근거 기록 절에 logs/파일.log 경로가 없다")

    for mark in LEFTOVER:
        if mark in text:
            problems.append(f"채우지 않은 자리 표시가 남아 있다: {mark}")
    return problems


def use_utf8_output():
    """출력을 UTF-8로 맞춘다. Windows의 파이썬은 파이프로 내보낼 때 cp949를 쓰므로,
    Claude Code가 이 출력을 읽거나 사람이 grep으로 넘길 때 한글이 깨진다(부록 A-4-4)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    use_utf8_output()
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("사용: python check_report.py <보고서.md>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"파일이 없다: {path}", file=sys.stderr)
        return 2
    problems = check(path.read_text(encoding="utf-8"))
    if problems:
        print(f"서식 위반 {len(problems)}건: {path}")
        for p in problems:
            print(f"- {p}")
        return 1
    print(f"서식 통과: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
