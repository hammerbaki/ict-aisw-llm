"""근거 추적 검사: 페르소나·친화도·문제 정의의 인용 표기가 실제 기록의 줄을 가리키는지 확인한다.

사용법
    python check_trace.py ch07/페르소나.md --records ch07/기록
    python check_trace.py ch07/페르소나.md --records ch07/기록 --report ch07/대조표.md
    python check_trace.py ch07/친화도.md ch07/문제정의.md --records ch07/기록

인용 표기
    [논의_01:L12]       기록 논의_01.md의 L12 한 줄
    [논의_01:L12-L14]   L12부터 L14까지 (L12-14로 써도 된다)

판정
    실패  인용한 기록 파일이나 줄이 없다, 또는 인용 표기의 형식이 틀렸다
    누락  근거 표기가 없는 주장 줄이 있다. '(가정)'(아직 확인하지 않은 추측)이나
          '(결정)'(작성자가 정한 범위)을 붙인 줄, '작성 정보'·'검토 기록'·'점검' 절은 제외
    경고  진행자의 질문(Q)이나 해석(메모)을 근거로 인용했다, 범위가 6줄 이상이다

    실패나 누락이 하나라도 있으면 종료 코드 1, 없으면 0이다.
    이 검사는 "그 줄이 있는가"만 본다. "그 줄이 주장을 뒷받침하는가"는 사람이
    --report로 만든 대조표를 읽고 판단한다.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recordfmt import EVIDENCE_SPEAKERS, RecordFormatError, load_records  # noqa: E402

CITATION = re.compile(r"^\[([^\[\]:\s]+):L(\d+)(?:\s*[-~]\s*L?(\d+))?\]$")
CANDIDATE = re.compile(r"\[[^\[\]]*?:\s*L[^\[\]]*\]")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}")
EXEMPT_MARKS = ("(가정)", "(결정)")
EXCLUDED_SECTIONS = ("작성 정보", "검토 기록", "점검", "검사 제외")
WIDE_RANGE = 6


def parse_citations(text):
    """줄 안의 인용 후보를 찾아 (정상 인용 목록, 형식 오류 목록)을 돌려준다."""
    good, bad = [], []
    for raw in CANDIDATE.findall(text):
        m = CITATION.match(raw.replace(" ", ""))
        if not m:
            bad.append(raw)
            continue
        start = int(m.group(2))
        end = int(m.group(3)) if m.group(3) else start
        good.append((raw, m.group(1), start, end))
    return good, bad


def claim_lines(lines):
    """근거가 있어야 하는 주장 줄을 고른다: 첫 '## ' 제목 뒤의 글머리 항목과 표의 본문 행."""
    out = []
    seen_h2 = False
    excluded = False
    for i, line in enumerate(lines, start=1):
        h = HEADING.match(line)
        if h:
            if len(h.group(1)) == 2:
                seen_h2 = True
            excluded = any(word in h.group(2) for word in EXCLUDED_SECTIONS)
            continue
        if not seen_h2 or excluded:
            continue
        stripped = line.strip()
        if stripped.startswith("|"):
            nxt = lines[i] if i < len(lines) else ""
            if TABLE_SEP.match(stripped) or TABLE_SEP.match(nxt.strip()):
                continue  # 구분 행과 머리 행
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if sum(len(c) for c in cells[1:]) < 4:
                continue  # 첫 열(항목 이름)만 있고 내용이 빈 행
            out.append((i, stripped))
            continue
        b = BULLET.match(line)
        if b and len(b.group(1).strip()) >= 4:
            out.append((i, stripped))
    return out


def check_file(path, records):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    fails, warns, missing, rows = [], [], [], []
    usage = Counter()
    count = 0
    for i, line in enumerate(lines, start=1):
        good, bad = parse_citations(line)
        for raw in bad:
            fails.append(f"{i}행: {raw} - 인용 표기의 형식이 틀렸다 (예: [논의_01:L12], [논의_01:L12-L14])")
        for raw, name, start, end in good:
            count += 1
            if name not in records:
                fails.append(f"{i}행: {raw} - 기록 파일 {name}.md가 없다")
                continue
            entries = records[name]
            if end < start:
                fails.append(f"{i}행: {raw} - 범위의 끝이 시작보다 작다")
                continue
            absent = [n for n in range(start, end + 1) if n not in entries]
            if absent:
                last = max(entries) if entries else 0
                shown = ", ".join(f"L{n}" for n in absent[:3])
                fails.append(f"{i}행: {raw} - {name}에 {shown}이 없다 (마지막 줄 L{last})")
                continue
            usage[name] += 1
            if end - start + 1 >= WIDE_RANGE:
                warns.append(f"{i}행: {raw} - 범위가 {end - start + 1}줄이다. 근거가 되는 줄로 좁힌다")
            for n in range(start, end + 1):
                speaker, said = entries[n]
                if speaker not in EVIDENCE_SPEAKERS:
                    who = "진행자의 질문(Q)" if speaker == "Q" else "진행자의 해석(메모)"
                    warns.append(f"{i}행: [{name}:L{n}] - {who}을 근거로 인용했다")
                rows.append((i, name, n, speaker, said, line.strip()))
    for i, text in claim_lines(lines):
        good, bad = parse_citations(text)
        if not good and not bad and not any(mark in text for mark in EXEMPT_MARKS):
            missing.append(f"{i}행: 근거 표기가 없는 주장: {text[:60]}")
    return {"count": count, "fails": fails, "warns": warns, "missing": missing,
            "rows": rows, "usage": usage}


def write_report(path, results):
    out = ["# 근거 대조표", "",
           "검사 스크립트는 줄이 있는지만 확인한다. 아래 표의 '기록의 줄'이 '주장'을 실제로 뒷받침하는지 사람이 판정해 마지막 열에 O, X, △를 적는다.",
           ""]
    for target, res in results:
        out += [f"## {target}", "", "| 주장(행) | 인용 | 화자 | 기록의 줄 | 판정 |", "|---|---|---|---|---|"]
        for i, name, n, speaker, said, claim in res["rows"]:
            claim_text = re.sub(r"\s*\[[^\]]*:L[^\]]*\]", "", claim).lstrip("-*| ").replace("|", "/")
            said_text = said.replace("|", "/")
            out.append(f"| {i}행: {claim_text[:50]} | {name}:L{n} | {speaker} | {said_text[:70]} | |")
        out.append("")
    # Windows에서도 줄 끝을 LF로 쓴다(write_text는 CRLF로 바꾼다). 저장소의 줄 끝을 운영체제와 상관없이 맞추기 위해서이다
    Path(path).write_bytes(("\n".join(out) + "\n").encode("utf-8"))


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="인용 표기가 실제 기록의 줄을 가리키는지 검사한다")
    parser.add_argument("targets", nargs="+", help="검사할 파일 (페르소나.md, 친화도.md, 문제정의.md)")
    parser.add_argument("--records", required=True, help="기록 파일이 있는 폴더 (예: ch07/기록)")
    parser.add_argument("--report", help="사람이 대조할 표를 이 경로에 마크다운으로 쓴다")
    args = parser.parse_args(argv)

    try:
        records = load_records(args.records)
    except RecordFormatError as e:
        print(f"[기록 형식 오류] {e}")
        return 2
    if not records:
        print(f"[기록 없음] {args.records}에 기록 파일(.md)이 없다")
        return 2
    summary = ", ".join(f"{k}: {len(v)}줄" for k, v in records.items())
    print(f"기록 {len(records)}개 ({summary})")

    total_fail = total_miss = total_warn = 0
    results = []
    for target in args.targets:
        res = check_file(target, records)
        results.append((target, res))
        print(f"\n검사 대상: {target}  인용 {res['count']}개")
        for msg in res["fails"]:
            print(f"[실패] {msg}")
        for msg in res["missing"]:
            print(f"[누락] {msg}")
        for msg in res["warns"]:
            print(f"[경고] {msg}")
        if res["usage"]:
            spread = ", ".join(f"{k} {v}회" for k, v in sorted(res["usage"].items()))
            print(f"기록별 인용: {spread}")
        total_fail += len(res["fails"])
        total_miss += len(res["missing"])
        total_warn += len(res["warns"])

    if args.report:
        write_report(args.report, results)
        print(f"\n대조표를 썼다: {args.report}")
    verdict = "통과" if total_fail == 0 and total_miss == 0 else "불통과"
    print(f"\n결과: {verdict} (실패 {total_fail}, 누락 {total_miss}, 경고 {total_warn})")
    return 0 if verdict == "통과" else 1


if __name__ == "__main__":
    sys.exit(main())
