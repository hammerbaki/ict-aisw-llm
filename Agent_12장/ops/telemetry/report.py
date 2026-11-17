"""운영 관측 보고: 서비스 기록, LLM 호출 기록, 에이전트 실행 기록을 모아 지표와 비용을 보고한다.

사용법(저장소 맨 위에서)
    python -m ops.telemetry.report
    python -m ops.telemetry.report --budget-usd 5 --out docs/운영/관측보고_2027-11.md
    python -m ops.telemetry.report --eval-run evals/runs/<실행> --price-as sim-a=claude-haiku-5-5

읽는 것
    logs/access.log, logs/error.log, logs/llm.log   서비스 운영 기록(--logs로 폴더를 바꾼다)
    ops/loop/logs/*.jsonl                            8장 루프 실행 기록(--loop)
    ops/multi/logs/<이슈>/events.jsonl                10장 멀티 에이전트 실행 기록(--multi)
    ops/multi/logs/<이슈>/<작업>_시도<n>.out           10장 구현 에이전트의 출력(Claude Code의 JSON이면 비용과 턴)
    git log의 커밋 꼬리말 Agent-Role, Agent-Task, Agent-Attempt   10장 에이전트 커밋(저장소 안에서 실행할 때)
    evals/runs/<실행>/llm.log                         평가 실행의 LLM 호출 기록(--eval-run, 선택)

종료 코드
    0  보고 완료(예산을 주지 않았거나 예산 안)
    2  예산 초과(--budget-usd보다 추정 비용이 크다)
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from ops.telemetry.logparse import read_jsonl, read_log

HERE = Path(__file__).resolve().parent
WARN_RATIO = 0.8   # 예산의 이 비율을 넘으면 주의를 띄운다


def percentile(values, q):
    """가장 가까운 순위 방식의 백분위수. 값이 없으면 None."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(q / 100 * len(ordered) + 0.4999))
    return ordered[min(rank, len(ordered)) - 1]


def route(path):
    """/api/jobs/12 같은 경로를 /api/jobs/{id}로 묶는다."""
    return re.sub(r"/\d+(?=/|$)", "/{id}", path)


def load_prices(path, aliases):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    prices = dict(data["models"])
    for alias, target in aliases.items():
        if target in prices:
            prices[alias] = prices[target]
    return prices, data


def cost_of(model, input_tokens, output_tokens, prices):
    """백만 토큰당 가격으로 비용을 어림한다. 가격표에 없는 모델이면 None."""
    price = prices.get(model)
    if price is None:
        return None
    return input_tokens / 1e6 * price["input_per_mtok"] + output_tokens / 1e6 * price["output_per_mtok"]


def service_section(access):
    lines = ["## 1. 서비스 지표 (access.log)", ""]
    if not access:
        return lines + ["기록이 없다.", ""]
    days = sorted({r["ts"][:10] for r in access})
    lines.append(f"- 기간: {days[0]} ~ {days[-1]} ({len(days)}일), 요청 {len(access):,}건")
    errors = sum(1 for r in access if r.get("status", 0) >= 500)
    lines.append(f"- 서버 오류(5xx) {errors}건, 비율 {errors / len(access):.2%}")
    lines += ["", "| 경로 | 요청 | 5xx | 4xx | 지연 p50(ms) | 지연 p95(ms) | 최대(ms) |", "|---|---|---|---|---|---|---|"]
    groups = defaultdict(list)
    for r in access:
        groups[f"{r.get('method', '?')} {route(r.get('path', '?'))}"].append(r)
    for key in sorted(groups, key=lambda k: -len(groups[k])):
        rows = groups[key]
        ok_ms = [r["ms"] for r in rows if r.get("status", 0) < 500 and "ms" in r]
        lines.append(f"| `{key}` | {len(rows)} | {sum(r['status'] >= 500 for r in rows)} | "
                     f"{sum(400 <= r['status'] < 500 for r in rows)} | {percentile(ok_ms, 50)} | "
                     f"{percentile(ok_ms, 95)} | {max(ok_ms) if ok_ms else None} |")
    lines += ["", "지연은 성공한 요청(5xx가 아닌 것)만으로 잰다. 실패한 요청의 지연은 따로 보아야 한다.", ""]
    return lines


def llm_section(llm, prices, title="## 2. LLM 호출 (llm.log)"):
    lines = [title, ""]
    if not llm:
        return lines + ["기록이 없다.", ""], 0.0, []
    table = defaultdict(lambda: {"calls": 0, "fail": 0, "in": 0, "out": 0})
    failures = Counter()
    by_day = defaultdict(float)
    unknown = set()
    for r in llm:
        key = (r.get("task", "?"), r.get("model", "?"))
        if "error" in r:
            table[key]["fail"] += 1
            failures[r["error"]] += 1
            continue
        table[key]["calls"] += 1
        table[key]["in"] += r.get("input_tokens", 0)
        table[key]["out"] += r.get("output_tokens", 0)
        cost = cost_of(r.get("model"), r.get("input_tokens", 0), r.get("output_tokens", 0), prices)
        if cost is None:
            unknown.add(r.get("model"))
        else:
            by_day[r["ts"][:10]] += cost
    total = 0.0
    lines += ["| 기능 | 모델 | 성공 | 실패 | 입력 토큰 | 출력 토큰 | 추정 비용(USD) |", "|---|---|---|---|---|---|---|"]
    for (task, model), v in sorted(table.items()):
        cost = cost_of(model, v["in"], v["out"], prices)
        total += cost or 0.0
        shown = f"{cost:.4f}" if cost is not None else "가격 없음"
        lines.append(f"| {task} | {model} | {v['calls']} | {v['fail']} | {v['in']:,} | {v['out']:,} | {shown} |")
    calls = sum(v["calls"] for v in table.values())
    fails = sum(v["fail"] for v in table.values())
    lines += ["", f"- 호출 {calls + fails}건 가운데 실패 {fails}건({fails / (calls + fails):.1%})"]
    if failures:
        lines.append("- 실패 유형: " + ", ".join(f"{name} {n}건" for name, n in failures.most_common()))
    if calls:
        lines.append(f"- 추정 비용 합계 {total:.4f} USD, 성공한 호출 1건당 {total / calls:.6f} USD")
    if by_day:
        peak = max(by_day, key=by_day.get)
        lines.append(f"- 하루 비용이 가장 큰 날: {peak} ({by_day[peak]:.4f} USD)")
    if unknown:
        lines.append(f"- 가격표에 없는 모델(비용 0으로 셈): {', '.join(sorted(map(str, unknown)))}")
    return lines + [""], total, sorted(unknown)


def touched_protected(run_rows):
    """실행에서 커밋된 시도가 보호 경로(테스트 등)를 바꾸었으면 그 경로들을 돌려준다."""
    start = next((r for r in run_rows if r.get("event") == "start"), {})
    # 루프 설정의 보호 경로에 tests/를 늘 더한다. 보호를 끄고 돌린 실행도 테스트를 고쳤으면 의심한다.
    protected = set(start.get("config", {}).get("protected") or []) | {"tests/"}
    touched = []
    for r in run_rows:
        if r.get("event") == "attempt" and r.get("decision") in ("commit", "checkpoint"):
            touched += [p for p in r.get("changed", []) if any(p.startswith(x) for x in protected)]
    return touched


def loop_section(rows):
    lines = ["## 3. 에이전트 루프 (8장 실행 기록)", ""]
    ends = [r for r in rows if r.get("event") == "end"]
    if not ends:
        return lines + ["기록이 없다.", ""], 0.0
    by_run = defaultdict(list)
    for r in rows:
        by_run[r.get("run_id")].append(r)
    attempts = [r for r in rows if r.get("event") == "attempt"]
    green = [e for e in ends if e["status"] == "green"]
    suspect = [e for e in green if touched_protected(by_run[e["run_id"]])]
    verified = [e for e in green if e not in suspect]
    handoff = [e for e in ends if e["status"] != "green"]
    spent = sum(e.get("spent_usd", 0.0) for e in ends)
    lines.append(f"- 실행 {len(ends)}건, green {len(green)}건, 그 가운데 보호 경로(테스트 등)를 고친 의심 성공 {len(suspect)}건")
    lines.append(f"- 검증된 작업 성공률 {len(verified) / len(ends):.0%} (green만 세면 {len(green) / len(ends):.0%})")
    if suspect:
        lines.append("- 의심 성공: " + ", ".join(
            f"{e['run_id']}({', '.join(touched_protected(by_run[e['run_id']]))})" for e in suspect))
    lines.append(f"- 사람에게 넘긴 실행 {len(handoff)}건: " +
                 ", ".join(f"{e['run_id']}({e['status']})" for e in handoff) if handoff else "- 사람에게 넘긴 실행 없음")
    lines.append(f"- 실행당 평균 시도 {len(attempts) / len(ends):.2f}회, 시도당 평균 턴 "
                 f"{sum(a.get('turns', 0) for a in attempts) / max(1, len(attempts)):.1f}")
    lines.append(f"- 추정 비용 합계 {spent:.2f} USD, 검증된 성공 1건당 {spent / max(1, len(verified)):.2f} USD")
    first_try = sum(1 for e in verified if e["attempts"] == 1)
    lines.append(f"- 첫 시도에 끝난 검증된 성공 {first_try}건 / {len(verified)}건")
    lines += ["", "| 실행 | 결과 | 시도 | 비용(USD) |", "|---|---|---|---|"]
    for e in ends:
        mark = " (의심)" if e in suspect else ""
        lines.append(f"| {e['run_id']} | {e['status']}{mark} | {e['attempts']} | {e.get('spent_usd', 0):.2f} |")
    return lines + [""], spent


OUT_NAME = re.compile(r"^(?P<task>T\d+)_시도(?P<attempt>\d+)\.out$")
EXCEPTIONS = ("merge_conflict", "merge_test_failed", "handed_to_human")   # 시스템이 풀지 못해 사람이 처리한 사건


def read_multi(base):
    """10장의 실행 기록을 이슈별로 읽는다: {이슈: {"events": [...], "outs": [...]}}.

    events는 ops/multi/lib.sh의 log_event가 쓴 줄(time, issue, actor, event, task, detail)이다.
    outs는 구현 에이전트 출력(<작업>_시도<n>.out)이다. 출력이 Claude Code의 JSON 결과
    (claude -p --output-format json)이면 total_cost_usd와 num_turns를 읽고, 아니면(가짜 에이전트) 비용을 None으로 둔다.
    """
    runs = {}
    for path in sorted(Path(base).glob("*/events.jsonl")):
        outs = []
        for out in sorted(path.parent.glob("*.out")):
            match = OUT_NAME.match(out.name)
            if not match:
                continue
            item = {"task": match["task"], "attempt": int(match["attempt"]), "cost_usd": None, "turns": None}
            try:
                data = json.loads(out.read_text(encoding="utf-8").strip().splitlines()[-1])
            except (OSError, IndexError, json.JSONDecodeError):
                data = None
            if isinstance(data, dict):
                item["cost_usd"] = data.get("total_cost_usd")
                item["turns"] = data.get("num_turns")
            outs.append(item)
        runs[path.parent.name] = {"events": read_jsonl([path]), "outs": outs}
    return runs


def parse_trailers(text):
    """git log 출력(커밋마다 「짧은 해시␟역할␟작업␟시도␞」)에서 Agent-Task 꼬리말이 있는 커밋만 고른다."""
    commits = []
    for chunk in text.split("\x1e"):
        parts = [p.strip() for p in chunk.strip("\n").split("\x1f")]
        if len(parts) != 4 or not parts[2]:
            continue
        sha, role, task, attempt = parts
        commits.append({"commit": sha, "role": role or "?", "task": task,
                        "attempt": int(attempt) if attempt.isdigit() else None})
    return commits


def agent_commits(repo="."):
    """저장소의 모든 브랜치에서 10장 구현 에이전트의 커밋 꼬리말을 읽는다. git이 없거나 저장소가 아니면 빈 목록."""
    fmt = ("%h%x1f%(trailers:key=Agent-Role,valueonly,separator=%x2C)"
           "%x1f%(trailers:key=Agent-Task,valueonly,separator=%x2C)"
           "%x1f%(trailers:key=Agent-Attempt,valueonly,separator=%x2C)%x1e")
    try:
        result = subprocess.run(["git", "-C", str(repo), "log", "--all", f"--format={fmt}"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_trailers(result.stdout) if result.returncode == 0 else []


def issue_summary(run):
    """이슈 하나의 사건에서 작업, 시도, 판정, 병합, 예외, 비용을 센다."""
    events = run["events"]
    dispatched = [e for e in events if e.get("event") == "dispatched"]
    # Orca 작업 공간처럼 사람이 세션에 지시를 넣은 경로(10장 핵심 실습)에는 dispatched 사건이 없다.
    # 그때는 판정·병합 사건에 나온 작업을 세고, 시도는 판정 횟수로 어림한다.
    tasks = sorted({e.get("task") for e in events
                    if e.get("event") in ("dispatched", "judged", "merged") and e.get("task")})
    merged = sorted({e.get("task") for e in events if e.get("event") == "merged"})
    judged = [e for e in events if e.get("event") == "judged"]
    exceptions = [e for e in events if e.get("event") in EXCEPTIONS]
    costs = [o["cost_usd"] for o in run["outs"] if isinstance(o["cost_usd"], (int, float))]
    if tasks and set(tasks) <= set(merged):
        status = "예외 처리 뒤 병합" if exceptions else "병합"
    else:
        status = "미완료"
    return {
        "tasks": tasks,
        "attempts": len(dispatched) if dispatched else len(judged),
        "no_dispatch": not dispatched and bool(judged),
        "judged": len(judged),
        "rejected": sum(1 for e in judged if "verdict=거부" in e.get("detail", "")),
        "merged": len(merged),
        "planned": sum(1 for e in events if e.get("actor") == "human" and e.get("event") == "merged"),
        "exceptions": exceptions,
        "outs": len(run["outs"]),
        "cost": sum(costs),
        "costed": len(costs),
        "status": status,
    }


def multi_section(runs, commits=None):
    lines = ["## 4. 멀티 에이전트 (10장 실행 기록)", ""]
    if not runs:
        return lines + ["기록이 없다.", ""], 0.0
    rows = {issue: issue_summary(run) for issue, run in sorted(runs.items())}
    clean = [i for i, s in rows.items() if s["status"] == "병합"]
    others = [f"{i}({s['status']})" for i, s in rows.items() if s["status"] != "병합"]
    tasks = sum(len(s["tasks"]) for s in rows.values())
    attempts = sum(s["attempts"] for s in rows.values())
    judged = sum(s["judged"] for s in rows.values())
    rejected = sum(s["rejected"] for s in rows.values())
    planned = sum(s["planned"] for s in rows.values())
    exceptions = Counter(e["event"] for s in rows.values() for e in s["exceptions"])
    spent = sum(s["cost"] for s in rows.values())
    outs = sum(s["outs"] for s in rows.values())
    costed = sum(s["costed"] for s in rows.values())
    merged = sum(s["merged"] for s in rows.values())
    lines.append(f"- 이슈 {len(rows)}건, 작업 {tasks}개, 예외 처리 없이 병합 {len(clean)}건"
                 + (", 그 밖 " + ", ".join(others) if others else ""))
    lines.append(f"- 시도 {attempts}회(재시도율 {max(0, attempts / max(1, tasks) - 1):.0%}), "
                 f"판정 {judged}회 가운데 거부 {rejected}회(다시 작업한 횟수)")
    no_dispatch = [i for i, s in rows.items() if s["no_dispatch"]]
    if no_dispatch:
        lines.append(f"- 실행 사건(dispatched)이 없는 이슈 {len(no_dispatch)}건({', '.join(no_dispatch)}): "
                     "사람이 작업 공간의 세션에 지시한 경로(Orca)이므로 시도는 판정 횟수로 셌다")
    lines.append(f"- 사람의 개입 {planned + sum(exceptions.values())}회: 계획된 병합 {planned}회, "
                 f"예외 처리 {sum(exceptions.values())}회"
                 + (" (" + ", ".join(f"{k} {v}" for k, v in sorted(exceptions.items())) + ")" if exceptions else ""))
    if costed:
        lines.append(f"- 추정 비용 합계 {spent:.2f} USD(구현 에이전트 출력 {outs}개 가운데 비용이 있는 {costed}개), "
                     f"이슈당 {spent / len(rows):.2f} USD, 병합된 작업 1개당 {spent / max(1, merged):.2f} USD")
    else:
        lines.append(f"- 비용: 구현 에이전트 출력 {outs}개에 비용이 없다(가짜 에이전트의 출력은 JSON이 아니다)")
    if commits:
        retried = sum(1 for c in commits if (c["attempt"] or 1) > 1)
        roles = Counter(c["role"] for c in commits)
        lines.append(f"- 커밋 꼬리말: Agent-Task가 붙은 커밋 {len(commits)}건("
                     + ", ".join(f"{r} {n}" for r, n in sorted(roles.items()))
                     + f"), 두 번째 이후 시도의 커밋 {retried}건")
    else:
        lines.append("- 커밋 꼬리말: Agent-Task가 붙은 커밋이 이 저장소에 없다")
    lines += ["", "| 이슈 | 작업 | 시도 | 판정 거부 | 병합 | 예외 처리 | 비용(USD) |", "|---|---|---|---|---|---|---|"]
    for issue, s in rows.items():
        cost = f"{s['cost']:.2f}" if s["costed"] else "없음"
        lines.append(f"| {issue} | {len(s['tasks'])} | {s['attempts']} | {s['rejected']} | {s['merged']} | "
                     f"{len(s['exceptions'])} | {cost} |")
    return lines + [""], spent


def budget_section(total, budget):
    lines = ["## 5. 예산", ""]
    if budget is None:
        return lines + [f"- 추정 비용 합계 {total:.2f} USD (예산을 주지 않았다)", ""], 0
    ratio = total / budget if budget else float("inf")
    if ratio > 1:
        state, code = "초과", 2
    elif ratio >= WARN_RATIO:
        state, code = "주의", 0
    else:
        state, code = "정상", 0
    lines.append(f"- 추정 비용 합계 {total:.2f} USD / 예산 {budget:.2f} USD ({ratio:.0%}) → **{state}**")
    lines.append(f"- 주의 기준은 예산의 {WARN_RATIO:.0%}, 초과하면 종료 코드 2로 알린다")
    return lines + [""], code


def main(argv=None):
    parser = argparse.ArgumentParser(description="jobprep 운영 관측 보고")
    parser.add_argument("--logs", default="logs")
    parser.add_argument("--loop", default="ops/loop/logs")
    parser.add_argument("--multi", default="ops/multi/logs", help="10장 실행 기록 폴더(이슈마다 하위 폴더)")
    parser.add_argument("--eval-run", default=None, help="평가 실행 폴더(그 안의 llm.log를 읽는다)")
    parser.add_argument("--prices", default=str(HERE / "prices.json"))
    parser.add_argument("--price-as", action="append", default=[], metavar="모델=가격표의모델",
                        help="가격표에 없는 모델을 다른 모델의 가격으로 어림한다(예: sim-a=claude-haiku-5-5)")
    parser.add_argument("--budget-usd", type=float, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    aliases = dict(item.split("=", 1) for item in args.price_as)
    prices, price_info = load_prices(args.prices, aliases)
    logs = Path(args.logs)
    access, bad_a = read_log(logs / "access.log")
    llm, bad_l = read_log(logs / "llm.log")
    loop_rows = read_jsonl(sorted(Path(args.loop).glob("*.jsonl"))) if Path(args.loop).exists() else []
    multi_runs = read_multi(args.multi) if Path(args.multi).exists() else {}

    out = ["# 운영 관측 보고", "",
           f"가격표: {price_info.get('source', '')} (확인 {price_info.get('checked', '')}). 비용은 모두 토큰 수로 어림한 값이며 청구액이 아니다.", ""]
    out += service_section(access)
    lines, llm_cost, _ = llm_section(llm, prices)
    out += lines
    lines, loop_cost = loop_section(loop_rows)
    out += lines
    lines, multi_cost = multi_section(multi_runs, agent_commits() if multi_runs else [])
    out += lines
    eval_cost = 0.0
    if args.eval_run:
        eval_llm, _ = read_log(Path(args.eval_run) / "llm.log")
        lines, eval_cost, _ = llm_section(eval_llm, prices, title=f"## 부록. 평가 실행의 LLM 호출 ({args.eval_run})")
        out += lines
    total = llm_cost + loop_cost + multi_cost + eval_cost
    lines, code = budget_section(total, args.budget_usd)
    out += lines
    if bad_a or bad_l:
        out.append(f"읽지 못한 줄: access.log {bad_a}줄, llm.log {bad_l}줄")
    text = "\n".join(out)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    return code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
