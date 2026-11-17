"""원 명세와 구현에서 다시 뽑은 명세(추출 명세)의 요구 ID 집합을 대조한다.

추출 명세는 표로 쓴다. 첫 칸은 추출 명세 자신의 ID(예: C-01), 「요구」 칸은 EARS 문장,
「대응」 칸은 그 요구가 대응하는 원 명세의 ID(여럿이면 쉼표로, 없으면 -)다.

    python 도구/spec_diff.py jobprep/docs/요구사항명세서.md --range REQ-080~089 \
        form=jobprep/docs/추출명세/form.md chat=../llm-service-lab-chat/jobprep/docs/추출명세/chat.md

내는 것
  [1] 원 명세의 요구 가운데 어떤 추출 명세에도 대응이 없는 것: 구현이 빠뜨렸거나 추출이 놓친 요구
  [2] 원 요구별 대응 표: 변형마다 어느 추출 요구가 대응하는가
  [3] 추출 명세에만 있는 요구(대응 -): 구현이 명세 없이 정한 동작. 명세의 빈틈 후보
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import read_tables, utf8_stdout  # noqa: E402

ID_RE = r"[A-Z]{1,6}(?:-[A-Z]{1,6})?-\d{2,3}"
ROW_ID = re.compile(rf"^\s*(?:\|\s*|[-*]\s+)?\**({ID_RE})\**")


def in_range(rid: str, spec: str | None) -> bool:
    """spec이 'REQ-080~089'이면 REQ-080부터 REQ-089까지만 참이다."""
    if not spec:
        return True
    start, _, end = spec.partition("~")
    head, _, lo = start.rpartition("-")
    hi = end.rpartition("-")[2] if end else lo
    tail = rid.rpartition("-")
    return tail[0] == head and tail[2].isdigit() and int(lo) <= int(tail[2]) <= int(hi)


def original_ids(path: str, prefix: str | None, id_range: str | None = None) -> list[str]:
    ids = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = ROW_ID.match(line)
        if m and m.group(1) not in ids and (not prefix or m.group(1).startswith(prefix)) \
                and in_range(m.group(1), id_range):
            ids.append(m.group(1))
    return ids


def extracted(path: str) -> list[dict]:
    items = []
    for header, rows in read_tables(path):
        map_col = next((i for i, h in enumerate(header) if "대응" in h), None)
        text_col = next((i for i, h in enumerate(header) if "요구" in h), 1)
        if map_col is None:
            continue
        for row in rows:
            m = re.fullmatch(rf"\**({ID_RE})\**", row[0]) if row else None
            if not m:
                continue
            maps = re.findall(ID_RE, row[map_col]) if map_col < len(row) else []
            items.append({"id": m.group(1), "text": row[text_col] if text_col < len(row) else "", "maps": maps})
    return items


def main() -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("original")
    ap.add_argument("extracted", nargs="+", help="이름=경로 (예: form=추출명세/form.md)")
    ap.add_argument("--range", dest="id_range", help="원 명세에서 이 범위의 요구만 본다(예: REQ-080~089)")
    ap.add_argument("--prefix", help="원 명세에서 이 글자로 시작하는 ID만 본다(예: REQ-06)")
    args = ap.parse_args()

    orig = original_ids(args.original, args.prefix, args.id_range)
    specs = {}
    for item in args.extracted:
        name, _, path = item.partition("=")
        specs[name] = extracted(path)
    scope = args.id_range or args.prefix
    print(f"원 명세 요구 {len(orig)}개" + (f" (범위 {scope})" if scope else ""))
    for name, items in specs.items():
        print(f"추출 명세 {name}: 요구 {len(items)}개, 대응 없음 {sum(1 for i in items if not i['maps'])}개")

    covered = {name: {} for name in specs}
    for name, items in specs.items():
        for it in items:
            for oid in it["maps"]:
                covered[name].setdefault(oid, []).append(it["id"])

    print("\n[1] 어떤 추출 명세에도 대응이 없는 원 요구")
    missing = [oid for oid in orig if not any(oid in covered[n] for n in specs)]
    print("  " + (", ".join(missing) if missing else "없음"))

    print("\n[2] 원 요구별 대응")
    names = list(specs)
    print("  | 원 요구 | " + " | ".join(names) + " |")
    print("  |---|" + "---|" * len(names))
    for oid in orig:
        cells = [", ".join(covered[n].get(oid, [])) or "(없음)" for n in names]
        print(f"  | {oid} | " + " | ".join(cells) + " |")

    unknown = sorted({m for n in names for it in specs[n] for m in it["maps"]} - set(orig))
    if unknown:
        print(f"\n  주의: 원 명세에 없는 ID를 대응으로 적었다: {', '.join(unknown)}")

    print("\n[3] 추출 명세에만 있는 요구 (명세의 빈틈 후보)")
    for name in names:
        extra = [it for it in specs[name] if not it["maps"]]
        print(f"  {name}: {len(extra)}개")
        for it in extra:
            print(f"    {it['id']} {it['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
