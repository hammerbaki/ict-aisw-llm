"""설계 문서와 요구사항 명세서 v2의 연결을 검사한다 (「LLM 서비스 개발」 7장).

사용법 (jobprep 폴더가 있는 곳에서)
    python check_design.py jobprep/docs
    python check_design.py jobprep/docs --strict     경고도 실패로 친다

검사하는 파일 (docs 폴더 기준)
    요구사항명세서.md        제목에 「요구」가 든 절에서 요구 ID(REQ-001)를, 「## 화면 목록」 표에서 화면 ID(SCR-01)를 읽는다
    설계/정보구조.md         사이트맵에 나오는 화면 ID
    설계/사용자흐름.md       흐름에 나오는 화면 ID와 요구 ID
    설계/여정지도.md         「## 여정 지도」 절의 표에서 칸마다 근거 표시([근거: ...] 또는 [가정])가 있는지

오류(종료 코드 1): 화면 목록이 없음, 화면 ID 중복, 요구가 연결되지 않은 화면, 명세에 없는 요구 ID,
                    화면 목록에 없는 화면 ID
경고(종료 코드 0, --strict이면 1): 화면에 연결되지 않은 기능 요구(절이나 ### 소제목에 「비기능」, 「품질」이 없는 곳의 요구), 사이트맵에 없는 화면,
                    근거 표시가 없는 여정 지도 칸
"""
import argparse
import re
import sys
from pathlib import Path

REQ = re.compile(r"REQ-\d{3}")
SCR = re.compile(r"SCR-\d{2}")
HEADING = re.compile(r"^(#{2,3})\s+(.*)$")
EVIDENCE = re.compile(r"\[근거:\s*[^\]\s][^\]]*\]|\[가정\]")
EXEMPT_ROWS = ("단계", "기회")
NONFUNCTIONAL = ("비기능", "품질")


def sections(text):
    """## 또는 ### 제목으로 나눈 (제목, 본문) 목록을 돌려준다. 코드 블록 안의 #은 제목으로 보지 않는다."""
    result, title, buf, in_code = [], "", [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        match = None if in_code else HEADING.match(line)
        if match and match.group(1) == "##":
            result.append((title, "\n".join(buf)))
            title, buf = match.group(2).strip(), []
        else:
            buf.append(line)
    result.append((title, "\n".join(buf)))
    return result


def table_rows(body):
    """마크다운 표의 데이터 행을 칸 목록으로 돌려준다(머리 행과 구분 행은 뺀다)."""
    rows, seen_header = [], False
    for line in body.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            seen_header = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        if not seen_header:
            seen_header = True
            continue
        rows.append(cells)
    return rows


def read_spec(path):
    text = path.read_text(encoding="utf-8")
    defined, functional, screens, errors = set(), set(), {}, []
    has_screen_list = False
    for title, body in sections(text):
        if "화면 목록" in title:
            has_screen_list = True
            for cells in table_rows(body):
                ids = SCR.findall(cells[0]) if cells else []
                if not ids:
                    continue
                sid = ids[0]
                if sid in screens:
                    errors.append(f"화면 ID가 화면 목록에 두 번 나온다: {sid}")
                screens[sid] = set(REQ.findall(" ".join(cells[1:])))
        elif "요구" in title:
            sub = title
            for line in body.splitlines():
                match = HEADING.match(line)
                if match and match.group(1) == "###":
                    sub = title + " " + match.group(2)
                    continue
                found = set(REQ.findall(line))
                defined |= found
                if not any(word in sub for word in NONFUNCTIONAL):
                    functional |= found
    if not has_screen_list:
        errors.append("명세서에 「## 화면 목록」 절이 없다")
    return defined, functional, screens, errors


def check_journey(path):
    warnings = []
    text = path.read_text(encoding="utf-8")
    for title, body in sections(text):
        if "여정 지도" not in title:
            continue
        for cells in table_rows(body):
            if not cells or cells[0].strip("* ").startswith(EXEMPT_ROWS):
                continue
            label = cells[0].strip("* ")
            for col, cell in enumerate(cells[1:], start=1):
                if cell and cell != "-" and not EVIDENCE.search(cell):
                    warnings.append(f"여정지도.md 「{label}」 행 {col}번째 단계: 근거 표시가 없다")
    return warnings


def run(docs, out=print):
    docs = Path(docs)
    spec = docs / "요구사항명세서.md"
    ia = docs / "설계" / "정보구조.md"
    flow = docs / "설계" / "사용자흐름.md"
    journey = docs / "설계" / "여정지도.md"
    errors, warnings = [], []
    for p in (spec, ia, flow):
        if not p.exists():
            errors.append(f"파일이 없다: {p.as_posix()}")
    if errors:
        return report(errors, warnings, out)

    defined, functional, screens, spec_errors = read_spec(spec)
    errors += spec_errors
    out(f"[검사] 요구사항명세서.md: 요구 {len(defined)}개(기능 요구 {len(functional)}개), 화면 {len(screens)}개")
    if not screens:
        if not spec_errors:
            errors.append("화면 목록 표에서 화면 ID(SCR-01 형식)를 하나도 찾지 못하였다")
        out("[검사] 화면 목록이 없어 나머지 검사를 하지 않았다")
        return report(errors, warnings, out)

    for sid, reqs in sorted(screens.items()):
        if not reqs:
            errors.append(f"{sid}: 화면 목록에 관련 요구가 없다")
        for rid in sorted(reqs - defined):
            errors.append(f"{sid}: 명세에 없는 요구 ID {rid}")

    ia_ids = set(SCR.findall(ia.read_text(encoding="utf-8")))
    flow_text = flow.read_text(encoding="utf-8")
    flow_ids, flow_reqs = set(SCR.findall(flow_text)), set(REQ.findall(flow_text))
    out(f"[검사] 정보구조.md: 화면 ID {len(ia_ids)}개")
    out(f"[검사] 사용자흐름.md: 화면 ID {len(flow_ids)}개, 요구 ID {len(flow_reqs)}개")
    for name, ids in (("정보구조.md", ia_ids), ("사용자흐름.md", flow_ids)):
        for sid in sorted(ids - set(screens)):
            errors.append(f"{name}: 화면 목록에 없는 화면 ID {sid}")
    for rid in sorted(flow_reqs - defined):
        errors.append(f"사용자흐름.md: 명세에 없는 요구 ID {rid}")

    linked = set().union(*screens.values()) if screens else set()
    for rid in sorted(functional - linked):
        warnings.append(f"{rid}: 어느 화면에도 연결되지 않은 기능 요구")
    for sid in sorted(set(screens) - ia_ids):
        warnings.append(f"{sid}: 사이트맵(정보구조.md)에 없는 화면")

    if journey.exists():
        warnings += check_journey(journey)
    else:
        warnings.append("설계/여정지도.md가 없어 근거 표시를 검사하지 않았다")
    return report(errors, warnings, out)


def report(errors, warnings, out):
    for e in errors:
        out(f"오류  {e}")
    for w in warnings:
        out(f"경고  {w}")
    out(f"오류 {len(errors)}건, 경고 {len(warnings)}건")
    return errors, warnings


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="설계 문서와 명세서 v2의 연결 검사")
    parser.add_argument("docs", help="jobprep/docs 폴더")
    parser.add_argument("--strict", action="store_true", help="경고도 실패로 친다")
    args = parser.parse_args(argv)
    errors, warnings = run(args.docs)
    failed = bool(errors) or (args.strict and bool(warnings))
    print("결과: " + ("실패" if failed else "통과"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
