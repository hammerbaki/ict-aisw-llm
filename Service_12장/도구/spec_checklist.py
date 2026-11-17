"""명세 충족 점검표(마크다운 표)를 집계해 충족률을 낸다.

점검표는 요구 ID가 첫 칸에 있고 머리글에 「판정」 칸이 있는 표다. 판정은 충족, 부분, 미충족, 해당없음 중 하나다.
충족률 = (충족 + 0.5 × 부분) / (전체 − 해당없음)

    python 도구/spec_checklist.py jobprep/docs/비교/점검표_form.md jobprep/docs/비교/점검표_chat.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import read_tables, utf8_stdout  # noqa: E402

ID = re.compile(r"^\**([A-Z]{2,6}(?:-[A-Z]{2,6})?-\d{2,3})\**$")
LABELS = ("충족", "부분", "미충족", "해당없음")


def tally(path: str) -> dict:
    counts = {k: 0 for k in LABELS}
    unknown = []
    for header, rows in read_tables(path):
        col = next((i for i, h in enumerate(header) if "판정" in h), None)
        if col is None:
            continue
        for row in rows:
            if not row or not ID.match(row[0]) or col >= len(row):
                continue
            verdict = row[col].replace(" ", "")
            if verdict in counts:
                counts[verdict] += 1
            else:
                unknown.append(f"{row[0]}: '{row[col]}'")
    counts["_unknown"] = unknown
    return counts


def main() -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    status = 0
    for f in args.files:
        c = tally(f)
        denom = sum(c[k] for k in LABELS) - c["해당없음"]
        rate = (c["충족"] + 0.5 * c["부분"]) / denom * 100 if denom else 0.0
        print(f"{Path(f).name}: 충족 {c['충족']} · 부분 {c['부분']} · 미충족 {c['미충족']} · 해당없음 {c['해당없음']} → 충족률 {rate:.1f}%")
        for u in c["_unknown"]:
            print(f"  판정을 읽지 못함 {u} (충족, 부분, 미충족, 해당없음 중 하나로 쓴다)")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
