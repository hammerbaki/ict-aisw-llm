"""운영 문서(운영요건.md, 역할정의.md)의 형식을 검사한다.

「LLM 서비스 개발」 6장의 EARS 점검을 운영 요건 명세에 맞게 줄인 것이다. 내용이 옳은지는 보지 않고,
사람이 판정하기 전에 기계로 걸러 낼 수 있는 형식만 본다.

    python ops/check/check_ops.py reqs docs/운영/운영요건.md
    python ops/check/check_ops.py roles docs/운영/역할정의.md --reqs docs/운영/운영요건.md

reqs 검사 (운영 요건 표의 각 행)
  - 요건 ID가 OR-<분류>-<두 자리 번호> 형식이고 겹치지 않는다. 분류는 SEC, REL, CON, REP 넷이다
  - 「분류」 칸이 보안, 신뢰성, 일관성, 재현성 가운데 하나이고 ID의 분류와 맞는다
  - 「문형」 칸이 EARS 다섯 문형 가운데 하나이고, 요구 문장에 그 문형의 표지가 있다
  - 요구 문장이 「~(해)야 한다」 또는 「~않아야 한다」로 끝난다(남겨야, 내야, 고쳐야 한다도 된다)
  - 「측정 방법」 칸이 비어 있지 않다(빈칸, -, 미정, 양식의 「 」 자리 표시는 빈 것으로 본다)
  - 모호한 말(적절히, 빠르게 등)은 경고로만 알린다
  - 요건이 모두 --min-total개(기본 15) 이상, 분류마다 --min-each개(기본 3) 이상이다

roles 검사 (역할마다 「### R<번호> 이름」 제목 아래의 항목 표)
  - 역할이 --min-roles개(기본 5) 이상이다
  - 역할마다 권한, 입력, 출력, 완료 조건, 사람 승인 지점 칸이 비어 있지 않다
  - --reqs를 주면, 「관련 운영 요건」에 적은 ID가 운영 요건 명세에 실제로 있는지 본다

종료 코드: 오류가 없으면 0, 있으면 1. 경고만 있으면 0이다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CATEGORIES = {"SEC": "보안", "REL": "신뢰성", "CON": "일관성", "REP": "재현성"}
ID_RE = re.compile(r"^OR-(SEC|REL|CON|REP)-(\d{2})$")
ID_ANY = re.compile(r"OR-(?:SEC|REL|CON|REP)-\d{2}")

# EARS 문형별로 요구 문장에 있어야 하는 표지(「LLM 서비스 개발」 6장의 우리말 틀)
PATTERNS = {
    "상시": None,
    "상태": re.compile(r"동안"),
    "이벤트": re.compile(r"면,"),
    "선택": re.compile(r"경우"),
    "원치 않는 상황": re.compile(r"^만약 .+면,"),
}
ENDING = re.compile(r"야 한다\.?$")
VAGUE = ("적절히", "적절한", "빠르게", "충분히", "가능한 한", "잘 ", "등을", "원활", "최대한", "신속")
EMPTY = {"", "-", "—", "미정", "없음", "todo", "tbd"}
ROLE_FIELDS = ("권한", "입력", "출력", "완료 조건", "사람 승인 지점")


def utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells = re.split(r"(?<!\\)\|", line)  # 칸 안의 \|(코드 속 파이프)는 나누지 않는다
    return [c.strip() for c in cells]


def read_tables(text: str) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """마크다운 표를 (머리글, [(줄 번호, 칸 목록)]) 목록으로 읽는다."""
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            header = split_row(lines[i])
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append((j + 1, split_row(lines[j])))
                j += 1
            tables.append((header, rows))
            i = j
        else:
            i += 1
    return tables


def is_empty(cell: str) -> bool:
    c = cell.strip().strip("*").strip()
    if c.lower() in EMPTY or "「」" in c:
        return True  # 빈칸, 자리 표시만 있는 칸, 양식의 빈 자리 「」가 남은 칸
    return "「" in c and "」" in c and len(re.sub(r"「[^」]*」", "", c).strip(" .,·/()")) == 0


def col(header: list[str], name: str) -> int | None:
    for i, h in enumerate(header):
        if name in h.replace(" ", ""):
            return i
    return None


def check_reqs(text: str, min_total: int = 15, min_each: int = 3) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[str, int] = {}
    counts = {k: 0 for k in CATEGORIES}

    for header, rows in read_tables(text):
        c_id = 0 if header and "ID" in header[0] else None
        c_cat, c_form = col(header, "분류"), col(header, "문형")
        c_req, c_meas = col(header, "요구"), col(header, "측정방법")
        if c_id is None or None in (c_cat, c_form, c_req):
            continue  # 요건 표가 아닌 표(형식 설명 등)는 건너뛴다
        if c_meas is None:
            errors.append(f"{rows[0][0] - 2 if rows else '?'}행 근처: 요건 표에 「측정 방법」 칸이 없다")
            continue
        for lineno, cells in rows:
            cells += [""] * (len(header) - len(cells))
            raw_id = cells[c_id].strip("* ")
            if not raw_id:
                continue  # 빈 행
            where = f"{lineno}행 {raw_id}"
            m = ID_RE.match(raw_id)
            if not m:
                errors.append(f"{where}: ID 형식이 OR-<SEC|REL|CON|REP>-<두 자리 번호>가 아니다")
                continue
            if raw_id in seen:
                errors.append(f"{where}: ID가 {seen[raw_id]}행과 겹친다")
            seen[raw_id] = lineno
            code = m.group(1)
            counts[code] += 1

            cat = cells[c_cat].strip("* ")
            if cat not in CATEGORIES.values():
                errors.append(f"{where}: 분류 칸의 값 「{cat}」이 보안, 신뢰성, 일관성, 재현성 가운데 하나가 아니다")
            elif cat != CATEGORIES[code]:
                errors.append(f"{where}: 분류 칸은 「{cat}」, ID의 분류는 {code}({CATEGORIES[code]})이다. 둘이 맞지 않는다")

            form = cells[c_form].strip("* ")
            req = cells[c_req].strip()
            if is_empty(req):
                errors.append(f"{where}: 요구 문장이 비어 있다")
            else:
                if form not in PATTERNS:
                    errors.append(f"{where}: 문형 칸의 값 「{form}」이 상시, 상태, 이벤트, 선택, 원치 않는 상황 가운데 하나가 아니다")
                elif PATTERNS[form] and not PATTERNS[form].search(req):
                    mark = {"상태": "「~인 동안,」", "이벤트": "「~하면,」", "선택": "「~인 경우,」",
                            "원치 않는 상황": "「만약 ~이면,」"}[form]
                    errors.append(f"{where}: {form} 문형인데 요구 문장에 {mark} 표지가 없다")
                if not ENDING.search(req.rstrip("*")):
                    errors.append(f"{where}: 요구 문장이 「~(해)야 한다.」 또는 「~않아야 한다.」로 끝나지 않는다")
                for word in VAGUE:
                    if word in req:
                        warnings.append(f"{where}: 모호한 말 「{word.strip()}」 → 수치나 관찰할 수 있는 조건으로 바꾼다")
            if is_empty(cells[c_meas]):
                errors.append(f"{where}: 측정 방법이 비어 있다")

    total = sum(counts.values())
    if total < min_total:
        errors.append(f"요건이 {total}개이다. {min_total}개 이상이어야 한다")
    for code, n in counts.items():
        if n < min_each:
            errors.append(f"{CATEGORIES[code]}({code}) 요건이 {n}개이다. {min_each}개 이상이어야 한다")
    return errors, warnings, {"total": total, **counts}


def req_ids(text: str) -> set[str]:
    ids = set()
    for _, rows in read_tables(text):
        for _, cells in rows:
            m = ID_RE.match(cells[0].strip("* ")) if cells else None
            if m:
                ids.add(cells[0].strip("* "))
    return ids


def check_roles(text: str, known_reqs: set[str] | None = None, min_roles: int = 5) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    parts = re.split(r"^###\s+(R\d+\s+.+)$", text, flags=re.M)
    roles = []
    for k in range(1, len(parts), 2):
        title, body = parts[k].strip(), parts[k + 1]
        fields: dict[str, str] = {}
        for header, rows in read_tables(body):
            if not header or "항목" not in header[0]:
                continue
            for _, cells in rows:
                if len(cells) >= 2:
                    fields[cells[0].strip("* ").replace(" ", "")] = cells[1]
        roles.append((title, fields))

    for title, fields in roles:
        for name in ROLE_FIELDS:
            value = fields.get(name.replace(" ", ""))
            if value is None:
                errors.append(f"{title}: 「{name}」 칸이 없다")
            elif is_empty(value):
                errors.append(f"{title}: 「{name}」 칸이 비어 있다")
        perm = fields.get("권한", "")
        if perm and not is_empty(perm) and "금지" not in perm:
            warnings.append(f"{title}: 권한 칸에 「금지」(하면 안 되는 일)가 없다 → 허용만 적으면 경계가 드러나지 않는다")
        if known_reqs is not None:
            rel = fields.get("관련운영요건", "")
            for rid in ID_ANY.findall(rel):
                if rid not in known_reqs:
                    errors.append(f"{title}: 관련 운영 요건 {rid}가 운영 요건 명세에 없다")
    if len(roles) < min_roles:
        errors.append(f"역할이 {len(roles)}개이다. {min_roles}개 이상이어야 한다(제목은 「### R1 이름」 꼴)")
    return errors, warnings, {"roles": len(roles)}


def report(path: str, errors: list[str], warnings: list[str], summary: str) -> int:
    print(f"{Path(path).name}: {summary}")
    for w in warnings:
        print(f"  경고 {w}")
    for e in errors:
        print(f"  오류 {e}")
    print("  결과: " + ("통과" if not errors else f"오류 {len(errors)}개") + (f", 경고 {len(warnings)}개" if warnings else ""))
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("reqs", help="운영 요건 명세를 검사한다")
    a.add_argument("path")
    a.add_argument("--min-total", type=int, default=15)
    a.add_argument("--min-each", type=int, default=3)
    b = sub.add_parser("roles", help="역할 정의서를 검사한다")
    b.add_argument("path")
    b.add_argument("--reqs", help="관련 운영 요건 ID를 대조할 운영 요건 명세")
    b.add_argument("--min-roles", type=int, default=5)
    args = ap.parse_args(argv)

    text = Path(args.path).read_text(encoding="utf-8")
    if args.cmd == "reqs":
        errors, warnings, s = check_reqs(text, args.min_total, args.min_each)
        summary = f"요건 {s['total']}개 (보안 {s['SEC']} · 신뢰성 {s['REL']} · 일관성 {s['CON']} · 재현성 {s['REP']})"
    else:
        known = req_ids(Path(args.reqs).read_text(encoding="utf-8")) if args.reqs else None
        errors, warnings, s = check_roles(text, known, args.min_roles)
        summary = f"역할 {s['roles']}개"
    return report(args.path, errors, warnings, summary)


if __name__ == "__main__":
    sys.exit(main())
