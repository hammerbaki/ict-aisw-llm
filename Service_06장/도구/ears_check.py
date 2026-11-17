"""EARS 문형 검사기: 요구사항 명세서(마크다운)의 요구 문장을 점검한다.

「LLM 서비스 개발」 6장 실습 키트의 도구다. 표준 라이브러리만 쓴다(Python 3.12 이상).

점검하는 것
  1. ID: 요구 문장(「~야 한다」 또는 shall)이 든 목록 줄마다 고유 ID(기본 REQ-001 꼴)가 있는가.
     같은 ID가 두 번 나오면 오류다.
  2. 문형: 문장이 EARS 다섯 문형(상시, 사건, 상태, 선택, 원치 않는 동작)이나 복합 문형의
     키워드 구조를 따르는가. 붙인 라벨과 문장의 구조가 맞는가.
  3. 응답: 주체(기본 「시스템」)가 「~은/는」으로 나오고, 문장이 「~야 한다」로 끝나는가.
     한 문장에 「~야 한다」가 둘 이상이면 요구를 둘로 나누라고 알린다.
  4. 모호한 말: 「잘」, 「적절히」, 「빠르게」 같은 확인할 수 없는 말이 있으면 경고한다.
  5. 수용 기준: AC-001-1 꼴의 수용 기준이 가리키는 요구가 명세에 있는가.
     수용 기준이 하나도 없는 요구는 경고한다.
  6. 추적표(--trace): 추적표에 나온 요구·수용 기준 ID가 명세에 있는가.
     명세에 있는데 추적표에 없는 요구는 경고한다.
     --problems 로 문제 정의 파일을 주면 추적표의 문제 ID(P-01 꼴)가 그 파일에 있는지도 본다.

한국어 문형 (이 과목의 약속)
  상시            시스템은 <응답>해야 한다.
  사건            <트리거>하면(할 때), 시스템은 <응답>해야 한다.
  상태            <상태>인 동안, 시스템은 <응답>해야 한다.
  선택            <기능>이 포함된 경우, 시스템은 <응답>해야 한다.
  원치 않는 동작  만약 <트리거>하면, (그러면) 시스템은 <응답>해야 한다.
  복합            <상태>인 동안 <트리거>하면, 시스템은 <응답>해야 한다.
영어 문형(The ... shall, When, While, Where, If ... then)도 받는다.

사용법
  python ears_check.py 명세.md
  python ears_check.py 명세.md --trace 추적표.md --problems ../ch05/문제정의.md
  python ears_check.py 명세.md --system 시스템 --system jobprep --strict

종료 코드: 오류가 없으면 0, 오류가 있으면 1(--strict 이면 경고도 오류로 센다), 파일이 없으면 2.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LABELS = {
    "상시": "상시", "유비쿼터스": "상시", "ubiquitous": "상시",
    "사건": "사건", "이벤트": "사건", "event": "사건", "event-driven": "사건",
    "상태": "상태", "state": "상태", "state-driven": "상태",
    "선택": "선택", "선택 기능": "선택", "optional": "선택", "optional feature": "선택",
    "원치 않는 동작": "원치 않는 동작", "원치않는 동작": "원치 않는 동작",
    "원치 않는 행위": "원치 않는 동작", "unwanted": "원치 않는 동작",
    "unwanted behaviour": "원치 않는 동작", "unwanted behavior": "원치 않는 동작",
    "복합": "복합", "complex": "복합",
}
PATTERNS = ["상시", "사건", "상태", "선택", "원치 않는 동작", "복합"]

VAGUE = ["적절히", "적절한", "적당히", "빠르게", "신속하게", "충분히", "충분한", "가능하면",
         "가능한 한", "필요 시", "필요시", "필요한 경우", "편리하게", "쉽게", "사용자 친화적",
         "직관적", "효율적", "등을", "등의", "기타"]
VAGUE_EN = ["appropriate", "user-friendly", "fast", "quickly", "easy", "as needed", "etc"]

SHALL_KO = re.compile(r"야\s*한다")
SHALL_KO_MID = re.compile(r"야\s*하(?:고|며|거나|지만)\s")
SHALL_EN = re.compile(r"\bshall\b", re.IGNORECASE)
TRAIL = re.compile(r"\s*(←.*|\((?:근거|출처|관련|화면|페르소나|문제|추측|관찰)[^)]*\))\s*$")


@dataclass
class Finding:
    level: str  # 오류 | 경고
    where: str
    message: str


@dataclass
class Requirement:
    rid: str
    label: str | None
    text: str
    line: int
    pattern: str | None = None


@dataclass
class Report:
    requirements: list[Requirement] = field(default_factory=list)
    criteria: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, where: str, message: str) -> None:
        self.findings.append(Finding(level, where, message))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "오류"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "경고"]


def strip_md(text: str) -> str:
    """굵게, 기울임, 코드 표시를 지우고 공백을 하나로 모은다."""
    text = re.sub(r"\*\*|__|`", "", text)
    return re.sub(r"\s+", " ", text).strip()


def body_lines(text: str):
    """코드 블록과 표를 뺀 (줄 번호, 줄) 목록을 돌려준다."""
    in_code = False
    for no, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.lstrip().startswith("|"):
            continue
        yield no, line


def clean_sentence(text: str) -> str:
    """문장 끝의 표시(← 고침, ← 추가)와 근거 괄호, 마침표를 떼어 낸다."""
    prev = None
    while prev != text:
        prev = text
        text = TRAIL.sub("", text).strip()
    return text.rstrip(".").strip()


def subject_regex(systems: list[str]) -> re.Pattern:
    names = "|".join(re.escape(s) for s in systems)
    return re.compile(rf"(?:^|,\s*|\s)(?:그러면\s+)?(?:{names})(?:은|는)\s")


def classify_ko(sentence: str, subj: re.Pattern) -> tuple[str | None, str | None]:
    """한국어 문장의 문형과, 맞지 않으면 그 까닭을 돌려준다."""
    m = subj.search(sentence)
    if not m:
        return None, "주체가 없다(「시스템은 ~해야 한다」 꼴이 아니다)"
    head = sentence[: m.start()].strip().rstrip(",").strip()
    if not head:
        return "상시", None
    has_state = "동안" in head
    trigger_end = head.endswith(("면", "때"))
    if head.startswith("만약"):
        if not trigger_end:
            return None, "「만약 ~하면」의 「~하면」이 없다"
        return ("복합" if has_state else "원치 않는 동작"), None
    if has_state and trigger_end:
        return "복합", None
    if head.endswith("동안"):
        return "상태", None
    if head.endswith(("경우", "경우에")):
        return "선택", None
    if head.endswith(("면", "때")):
        return "사건", None
    return None, f"조건절 「{head[-12:]}」이 문형의 키워드(~하면, ~할 때, ~인 동안, ~인 경우, 만약 ~하면)로 끝나지 않는다"


def classify_en(sentence: str) -> tuple[str | None, str | None]:
    s = sentence.strip()
    low = s.lower()
    if not re.search(r"\bthe\s+\S+.*\bshall\b", low):
        return None, "\"the <system> shall <response>\" 꼴이 아니다"
    if low.startswith("if "):
        if " then " not in low:
            return None, "If 문형에 then 이 없다"
        return ("복합" if " while " in low else "원치 않는 동작"), None
    if low.startswith("while "):
        return ("복합" if re.search(r",\s*when\s", low) else "상태"), None
    if low.startswith("when "):
        return "사건", None
    if low.startswith("where "):
        return "선택", None
    if low.startswith("the "):
        return "상시", None
    return None, "문형의 키워드(When, While, Where, If ... then)로 시작하지 않는다"


def parse_requirement(line: str, id_re: re.Pattern):
    """목록 줄에서 라벨, ID, 문장을 꺼낸다. 요구 줄이 아니면 None."""
    m = re.match(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$", line)
    if not m:
        return None
    rest = strip_md(m.group(1))
    label = None
    lm = re.match(r"^\[([^\]]+)\]\s*", rest)
    if lm:
        label, rest = lm.group(1).strip(), rest[lm.end():]
    im = re.match(rf"^({id_re.pattern})\s*[:.)]?\s*", rest)
    rid = None
    if im:
        rid, rest = im.group(1), rest[im.end():]
        lm2 = re.match(r"^\[([^\]]+)\]\s*", rest)
        if lm2 and label is None:
            label, rest = lm2.group(1).strip(), rest[lm2.end():]
    return label, rid, rest.strip()


def check_spec(text: str, systems: list[str], id_pattern: str = r"REQ-\d{2,3}") -> Report:
    report = Report()
    id_re = re.compile(id_pattern)
    ac_re = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(?:\*\*)?(AC-(\d{2,3})-\d+)")
    subj = subject_regex(systems)
    seen: dict[str, int] = {}
    for no, line in body_lines(text):
        acm = ac_re.match(line)
        if acm:
            report.criteria[acm.group(1)] = no
            continue
        parsed = parse_requirement(line, id_re)
        if parsed is None:
            continue
        label, rid, sentence = parsed
        is_req = SHALL_KO.search(sentence) or SHALL_EN.search(sentence)
        if not is_req and rid is None:
            continue
        where = f"{no}행"
        if rid is None:
            report.add("오류", where, f"ID가 없는 요구 문장이다: 「{sentence[:30]}…」")
            continue
        if rid in seen:
            report.add("오류", rid, f"ID가 겹친다({seen[rid]}행과 {no}행)")
            continue
        seen[rid] = no
        req = Requirement(rid, label, sentence, no)
        report.requirements.append(req)
        check_sentence(req, subj, report)
    check_criteria(report)
    return report


def check_sentence(req: Requirement, subj: re.Pattern, report: Report) -> None:
    sentence = clean_sentence(req.text)
    english = SHALL_EN.search(sentence) is not None and not SHALL_KO.search(sentence)
    count = (len(SHALL_EN.findall(sentence)) if english
             else len(SHALL_KO.findall(sentence)) + len(SHALL_KO_MID.findall(sentence)))
    if count == 0:
        report.add("오류", req.rid, "응답이 「~야 한다」(shall)로 끝나지 않는다")
        check_vague(req, sentence, english, report)
        return
    if count > 1:
        report.add("오류", req.rid, "한 문장에 요구가 둘 이상이다. 문장을 나누고 ID를 따로 붙인다")
    if not english and not re.search(r"야\s*한다$", sentence):
        report.add("오류", req.rid, "문장이 「~야 한다.」로 끝나지 않는다")
    pattern, why = classify_en(sentence) if english else classify_ko(sentence, subj)
    req.pattern = pattern
    if pattern is None:
        report.add("오류", req.rid, f"문형을 알 수 없다: {why}")
    if req.label is None:
        report.add("경고", req.rid, f"문형 라벨이 없다(문장 구조는 {pattern or '알 수 없음'})")
    else:
        norm = LABELS.get(req.label.strip().lower(), LABELS.get(req.label.strip()))
        if norm is None:
            report.add("오류", req.rid, f"모르는 라벨 [{req.label}]")
        elif pattern is not None and norm != pattern:
            report.add("오류", req.rid, f"라벨은 [{norm}]인데 문장 구조는 [{pattern}]이다")
    check_vague(req, sentence, english, report)


def check_vague(req: Requirement, sentence: str, english: bool, report: Report) -> None:
    words = VAGUE_EN if english else VAGUE
    hits = [w for w in words if (re.search(rf"\b{re.escape(w)}\b", sentence, re.I) if english else w in sentence)]
    if not english and re.search(r"(^|\s)잘(\s|$)", sentence):
        hits.insert(0, "잘")
    if hits:
        report.add("경고", req.rid, "확인할 수 없는 말이 있다: " + ", ".join(f"「{w}」" for w in hits))


def check_criteria(report: Report) -> None:
    ids = {r.rid for r in report.requirements}
    covered = set()
    for ac in report.criteria:
        num = re.match(r"AC-(\d{2,3})-\d+", ac).group(1)
        target = next((rid for rid in ids if rid.split("-")[-1] == num), None)
        if target is None:
            report.add("오류", ac, f"가리키는 요구 REQ-{num}이 명세에 없다")
        else:
            covered.add(target)
    if report.criteria:
        for r in report.requirements:
            if r.rid not in covered:
                report.add("경고", r.rid, "수용 기준(AC)이 없다")


def check_trace(report: Report, trace_text: str, problems_text: str | None = None,
                id_pattern: str = r"REQ-\d{2,3}") -> dict:
    id_re = re.compile(id_pattern)
    in_trace, ac_in_trace, p_in_trace = set(), set(), set()
    for line in trace_text.splitlines():
        if not line.lstrip().startswith("|") or re.match(r"^\s*\|[-: |]+\|\s*$", line):
            continue
        in_trace.update(id_re.findall(line))
        ac_in_trace.update(re.findall(r"AC-\d{2,3}-\d+", line))
        p_in_trace.update(re.findall(r"\bP-\d{2}\b", line))
    spec_ids = {r.rid for r in report.requirements}
    for rid in sorted(in_trace - spec_ids):
        report.add("오류", "추적표", f"{rid}가 명세에 없다")
    for ac in sorted(ac_in_trace - set(report.criteria)):
        report.add("오류", "추적표", f"{ac}가 명세에 없다")
    for rid in sorted(spec_ids - in_trace):
        report.add("경고", rid, "추적표에 없다(어느 문제 정의에서 왔는지 모른다)")
    if problems_text is not None:
        defined = set(re.findall(r"\bP-\d{2}\b", problems_text))
        for p in sorted(p_in_trace - defined):
            report.add("오류", "추적표", f"{p}가 문제 정의 파일에 없다")
    return {"요구": len(in_trace), "수용 기준": len(ac_in_trace), "문제": len(p_in_trace)}


def render(report: Report, trace_summary: dict | None = None) -> str:
    out = []
    by_id: dict[str, list[Finding]] = {}
    for f in report.findings:
        by_id.setdefault(f.where, []).append(f)
    for r in report.requirements:
        fs = by_id.pop(r.rid, [])
        mark = "오류" if any(f.level == "오류" for f in fs) else ("경고" if fs else "통과")
        out.append(f"{r.rid:<8} [{r.pattern or '?'}] {mark}")
        for f in fs:
            out.append(f"         - {f.level}: {f.message}")
    for where, fs in by_id.items():
        for f in fs:
            out.append(f"{where:<8} {f.level}: {f.message}")
    dist = {p: sum(1 for r in report.requirements if r.pattern == p) for p in PATTERNS}
    out.append("")
    out.append("문형 분포: " + ", ".join(f"{p} {n}" for p, n in dist.items()))
    empty = [p for p in ("사건", "원치 않는 동작") if dist[p] == 0]
    if report.requirements and empty:
        out.append("빈 문형: " + ", ".join(empty) + " (사용자의 동작이나 오류 상황을 정하지 않았을 수 있다)")
    if trace_summary is not None:
        out.append("추적표: " + ", ".join(f"{k} {v}개" for k, v in trace_summary.items()))
    out.append(f"요약: 요구 {len(report.requirements)}개, 수용 기준 {len(report.criteria)}개, "
               f"오류 {len(report.errors)}건, 경고 {len(report.warnings)}건")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="EARS 문형 검사기")
    ap.add_argument("spec", help="요구사항 명세서(.md)")
    ap.add_argument("--trace", help="추적표(.md)")
    ap.add_argument("--problems", help="문제 정의 파일(.md). 추적표의 P-ID를 대조한다")
    ap.add_argument("--system", action="append", help="주체 이름(여러 번 줄 수 있다). 기본: 시스템")
    ap.add_argument("--id", default=r"REQ-\d{2,3}", help="요구 ID의 정규식. 기본: REQ-\\d{2,3}")
    ap.add_argument("--strict", action="store_true", help="경고도 오류로 센다")
    args = ap.parse_args(argv)
    paths = [args.spec] + [p for p in (args.trace, args.problems) if p]
    for p in paths:
        if not Path(p).is_file():
            print(f"파일이 없다: {p}")
            return 2
    systems = args.system or ["시스템"]
    report = check_spec(Path(args.spec).read_text(encoding="utf-8"), systems, args.id)
    summary = None
    if args.trace:
        problems = Path(args.problems).read_text(encoding="utf-8") if args.problems else None
        summary = check_trace(report, Path(args.trace).read_text(encoding="utf-8"), problems, args.id)
    print(render(report, summary))
    failed = report.errors or (args.strict and report.warnings)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
