"""도구들이 함께 쓰는 함수. 직접 실행하지 않는다."""
from __future__ import annotations

import sys
from pathlib import Path


def utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def read_tables(path: str | Path) -> list[tuple[list[str], list[list[str]]]]:
    """마크다운 파일의 표를 (머리글, 행 목록)으로 돌려준다."""
    tables, header, rows = [], None, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if header is None:
                header = cells
            elif all(set(c) <= set("-: ") for c in cells):
                continue
            else:
                rows.append(cells)
        else:
            if header is not None:
                tables.append((header, rows))
            header, rows = None, []
    if header is not None:
        tables.append((header, rows))
    return tables
