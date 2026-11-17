#!/usr/bin/env python3
"""jobprep 운영 기록(logs/)에서 하루치 사실을 뽑아 요약한다.

장애 보고서 스킬(incident-report)이 보고서를 쓰기 전에 실행하는 스크립트이다.
모델이 기록 수백 줄을 직접 세지 않게 하고, 건수와 시각은 이 스크립트의 출력만 근거로 삼게 한다.
표준 라이브러리만 쓴다(가상 환경이 없어도 python으로 돈다. Windows의 Git Bash에는 python3이 없다).

사용:
    python log_summary.py --date 2027-09-08
    python log_summary.py --date 2027-09-08 --logs ../jobprep/logs --slow-ms 5000

출력은 마크다운이다. 종료 코드: 0 정상, 2 입력 오류(날짜 형식, 기록 폴더 없음).
"""
import argparse
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (\w+) (\S+)\s*(.*)$")
PAIR_RE = re.compile(r'(\w+)=("[^"]*"|\S+)')

GAP_MINUTES = 30      # 같은 오류가 이 간격 안에 이어지면 한 묶음으로 본다
INCIDENT_MIN = 3      # 묶음 하나가 이 건수 이상이면 장애 후보로 본다
SLOW_MS = 5000        # 이 처리 시간(밀리초) 이상이면 느린 요청으로 본다


def parse_line(line):
    """기록 한 줄을 사전으로 바꾼다. 형식이 맞지 않으면 None."""
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    date, time, level, logger, rest = m.groups()
    fields = {}
    for key, value in PAIR_RE.findall(rest):
        fields[key] = value[1:-1] if value.startswith('"') else value
    return {"date": date, "time": time, "level": level, "logger": logger, "fields": fields}


def read_day(path, date):
    """파일에서 그날의 기록만 읽는다. 파일이 없으면 빈 목록."""
    path = Path(path)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = parse_line(line)
        if rec and rec["date"] == date:
            records.append(rec)
    return records


def minutes(time_text):
    h, m, s = (int(x) for x in time_text.split(":"))
    return h * 60 + m + s / 60


def group_errors(errors, gap=GAP_MINUTES):
    """ERROR 기록을 (경로, 상태, 오류 이름, 상세)가 같고 간격이 gap분 이내인 것끼리 묶는다."""
    groups = []
    for rec in sorted(errors, key=lambda r: r["time"]):
        f = rec["fields"]
        key = (f.get("path", "-"), f.get("status", "-"), f.get("error", "-"), f.get("detail", ""))
        last = next((g for g in reversed(groups) if g["key"] == key), None)
        if last and minutes(rec["time"]) - minutes(last["end"]) <= gap:
            last["end"] = rec["time"]
            last["count"] += 1
        else:
            groups.append({"key": key, "start": rec["time"], "end": rec["time"], "count": 1})
    return groups


def group_slow(access, slow_ms=SLOW_MS, gap=GAP_MINUTES):
    """처리 시간이 slow_ms 이상인 요청을 경로별로, 간격 gap분 이내끼리 묶는다."""
    groups = []
    slow = [r for r in access if int(r["fields"].get("ms", "0")) >= slow_ms]
    for rec in sorted(slow, key=lambda r: r["time"]):
        path = rec["fields"].get("path", "-")
        ms = int(rec["fields"]["ms"])
        last = next((g for g in reversed(groups) if g["path"] == path), None)
        if last and minutes(rec["time"]) - minutes(last["end"]) <= gap:
            last["end"] = rec["time"]
            last["count"] += 1
            last["max_ms"] = max(last["max_ms"], ms)
        else:
            groups.append({"path": path, "start": rec["time"], "end": rec["time"], "count": 1, "max_ms": ms})
    return groups


def status_class(code):
    return f"{code[0]}xx" if code[:1].isdigit() else "기타"


def summarize(logs_dir, date, slow_ms=SLOW_MS):
    """하루치 요약을 사전으로 돌려준다(테스트가 이 값을 확인한다)."""
    logs_dir = Path(logs_dir)
    access = read_day(logs_dir / "access.log", date)
    error_log = read_day(logs_dir / "error.log", date)
    llm = read_day(logs_dir / "llm.log", date)

    classes = Counter(status_class(r["fields"].get("status", "")) for r in access)
    errors = [r for r in error_log if r["level"] == "ERROR"]
    llm_fail = Counter(r["fields"]["error"] for r in llm if "error" in r["fields"])
    llm_ok = [r for r in llm if "error" not in r["fields"]]
    error_groups = group_errors(errors)
    slow_groups = group_slow(access, slow_ms)
    candidates = [g for g in error_groups if g["count"] >= INCIDENT_MIN]
    candidates += [g for g in slow_groups if g["count"] >= INCIDENT_MIN]
    return {
        "date": date,
        "logs": str(logs_dir),
        "requests": len(access),
        "classes": dict(classes),
        "error_groups": error_groups,
        "slow_groups": slow_groups,
        "llm_calls": len(llm),
        "llm_fail": dict(llm_fail),
        "tokens_in": sum(int(r["fields"].get("input_tokens", 0)) for r in llm_ok),
        "tokens_out": sum(int(r["fields"].get("output_tokens", 0)) for r in llm_ok),
        "candidates": len(candidates),
        "slow_ms": slow_ms,
    }


def render(s):
    """요약 사전을 마크다운으로 바꾼다."""
    out = [f"# 운영 기록 요약: {s['date']}", "", f"- 기록 폴더: {s['logs']}"]
    if s["requests"] == 0:
        out += [f"- 요청: 0건. 이 날짜의 access.log 기록이 없다(날짜와 기록 폴더를 확인한다)", ""]
        return "\n".join(out)
    cls = ", ".join(f"{k} {v}" for k, v in sorted(s["classes"].items()))
    out += [f"- 요청: {s['requests']}건 ({cls})", ""]

    out += ["## 오류 묶음 (logs/error.log, ERROR)", ""]
    if s["error_groups"]:
        out += ["| 시작 | 끝 | 경로 | 상태 | 오류 | 상세 | 건수 |", "|---|---|---|---|---|---|---|"]
        for g in s["error_groups"]:
            path, status, error, detail = g["key"]
            out.append(f"| {g['start']} | {g['end']} | {path} | {status} | {error} | {detail} | {g['count']} |")
    else:
        out.append("- 없음")
    out.append("")

    out += [f"## 느린 요청 묶음 (logs/access.log, {s['slow_ms']}ms 이상)", ""]
    if s["slow_groups"]:
        out += ["| 시작 | 끝 | 경로 | 건수 | 최대 ms |", "|---|---|---|---|---|"]
        for g in s["slow_groups"]:
            out.append(f"| {g['start']} | {g['end']} | {g['path']} | {g['count']} | {g['max_ms']} |")
    else:
        out.append("- 없음")
    out.append("")

    fail = ", ".join(f"{k} {v}" for k, v in sorted(s["llm_fail"].items())) or "없음"
    out += ["## LLM 호출 (logs/llm.log)", "",
            f"- 호출 {s['llm_calls']}건, 실패: {fail}",
            f"- 성공 호출의 토큰: 입력 {s['tokens_in']}, 출력 {s['tokens_out']}", ""]

    out += ["## 판정", "",
            f"- 장애 후보: {s['candidates']}건 (같은 묶음이 {INCIDENT_MIN}건 이상인 것)",
            "- 원인은 이 요약이 정하지 않는다. 보고서의 원인 절은 근거 기록과 함께 쓰고, 근거가 없으면 '확인 필요'로 둔다", ""]
    return "\n".join(out)


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
    parser = argparse.ArgumentParser(description="jobprep 운영 기록 하루치 요약")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--logs", default="logs", help="기록 폴더(기본: logs)")
    parser.add_argument("--slow-ms", type=int, default=SLOW_MS, help="느린 요청 기준(밀리초)")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            raise ValueError(args.date)
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"날짜 형식이 아니다: {args.date} (예: 2027-09-08)", file=sys.stderr)
        return 2
    if not Path(args.logs).is_dir():
        print(f"기록 폴더가 없다: {args.logs}", file=sys.stderr)
        return 2
    print(render(summarize(args.logs, args.date, args.slow_ms)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
