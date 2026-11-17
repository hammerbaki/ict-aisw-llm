"""fix_until_green: 테스트가 통과할 때까지 에이전트에게 고치게 하는 무인 루프.

루프의 여섯 부분은 다음과 같다.
    입력    지금 실패하는 테스트와 그 출력
    실행    에이전트 명령(AGENT_CMD) 한 번. 기본값은 claude -p
    판정    판정 명령(JUDGE_CMD, 기본값 pytest -q)의 종료 코드
    되돌림  진전이 없거나 규칙을 어긴 시도는 git restore로 버리고, 진전이 있으면 커밋으로 남긴다
    재시도  실패 출력의 요약을 다음 시도의 지시문에 붙인다
    종료    통과, 재시도 상한, 비용 상한, 시간 상한 가운데 먼저 닿는 것

사용법 (저장소 맨 위에서, 작업 트리가 깨끗한 상태로)
    python ops/loop/fix_until_green.py
    AGENT_CMD="python ops/loop/fake_agent.py" FAKE_SCENARIO=success python ops/loop/fix_until_green.py

환경 변수 (괄호 안은 기본값)
    AGENT_CMD             에이전트 명령 (claude). 가짜 에이전트는 "python ops/loop/fake_agent.py"
    LOOP_MAX_ATTEMPTS     재시도 상한, 곧 시도 횟수의 상한 (3)
    LOOP_BUDGET_USD       루프 전체의 비용 상한, 달러 (1.00)
    LOOP_RUN_BUDGET_USD   시도 한 번의 비용 상한, 달러 (0.50). claude의 --max-budget-usd로 넘긴다
    LOOP_MIN_RUN_BUDGET   남은 예산이 이보다 적으면 다음 시도를 시작하지 않는다 (0.10)
    LOOP_MAX_TURNS        시도 한 번의 턴 상한 (15). claude의 --max-turns로 넘긴다
    LOOP_ATTEMPT_TIMEOUT  시도 한 번의 시간 상한, 초 (600)
    LOOP_MAX_SECONDS      루프 전체의 시간 상한, 초 (1800)
    JUDGE_CMD             판정 명령 (지금 쓰는 파이썬으로 -m pytest -q)
    LOOP_PROTECTED        에이전트가 고치면 안 되는 경로, 쉼표로 구분
    LOOP_RUN_ID           실행 이름 (시각, 예: 20271110-093000)

종료 코드
    0 통과(처음부터 통과였던 경우 포함)   1 재시도 상한 도달   2 시작 조건 실패
    3 비용 또는 시간 상한 도달           4 판정 불가(테스트가 수집되지 않음)
1, 3, 4이면 ops/loop/reports/<실행 이름>.md에 사람에게 넘기는 보고서를 쓴다.
모든 시도는 ops/loop/logs/<실행 이름>.jsonl에 한 줄씩 기록한다.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = "ops/loop/logs"
REPORT_DIR = "ops/loop/reports"
EXCLUDED = (LOG_DIR + "/", REPORT_DIR + "/")  # 루프가 쓰는 곳. 변경 검사에서 뺀다

DEFAULT_PROTECTED = "tests/,pytest.ini,conftest.py,.claude/,ops/,.github/,requirements.txt"

# 시도 한 번에 에이전트가 쓸 수 있는 도구. 나머지는 --permission-mode dontAsk가 거부한다.
# Bash 규칙은 명령의 글자에 맞춘다. 루프가 PATH 맨 앞에 가상 환경의 폴더를 넣으므로(run_agent),
# 에이전트는 경로 없이 python, pytest로 부른다. .venv/Scripts/python 같은 경로 호출은 규칙에 맞지 않아 거부된다.
ALLOWED_TOOLS = [
    "Read", "Edit", "Bash(pytest)", "Bash(pytest *)",
    "Bash(python -m pytest)", "Bash(python -m pytest *)",
]
# 허용 목록과 겹쳐도 거부가 먼저다. 루프가 할 일(커밋)과 위험한 명령, 보호 경로의 편집을 막는다.
DENIED_TOOLS = [
    "Bash(git commit *)", "Bash(git push *)", "Bash(git reset *)", "Bash(git checkout *)",
    "Bash(rm *)", "Edit(/tests/**)", "Edit(/.claude/**)", "Edit(/ops/**)", "Read(/.env)",
]
APPEND_PROMPT = (
    "이 실행은 무인 루프의 한 시도이다. 사람에게 질문할 수 없다. "
    "지시된 범위 밖의 파일을 고치지 않는다. 마지막 줄에 OK 또는 FAIL만 쓴다."
)
SUMMARY_PATTERN = re.compile(r"(\d+) (failed|error|errors)\b")
EXIT = {"green": 0, "already_green": 0, "gave_up": 1, "precondition": 2,
        "budget": 3, "time": 3, "suspicious": 4}


# ---------------------------------------------------------------- 설정과 기록

def setting(name, default, kind=str):
    value = os.environ.get(name)
    return default if value in (None, "") else kind(value)


class Config:
    def __init__(self):
        self.agent_cmd = setting("AGENT_CMD", "claude")
        self.max_attempts = setting("LOOP_MAX_ATTEMPTS", 3, int)
        self.budget = setting("LOOP_BUDGET_USD", 1.00, float)
        self.run_budget = setting("LOOP_RUN_BUDGET_USD", 0.50, float)
        self.min_run_budget = setting("LOOP_MIN_RUN_BUDGET", 0.10, float)
        self.max_turns = setting("LOOP_MAX_TURNS", 15, int)
        self.attempt_timeout = setting("LOOP_ATTEMPT_TIMEOUT", 600, float)
        self.max_seconds = setting("LOOP_MAX_SECONDS", 1800, float)
        self.judge_cmd = setting("JUDGE_CMD", f'"{Path(sys.executable).as_posix()}" -m pytest -q')
        self.protected = [p.strip() for p in setting("LOOP_PROTECTED", DEFAULT_PROTECTED).split(",") if p.strip()]
        self.run_id = setting("LOOP_RUN_ID", datetime.now().strftime("%Y%m%d-%H%M%S"))

    def as_dict(self):
        return dict(vars(self))


class JsonlLog:
    """한 줄에 JSON 객체 하나(JSON Lines). 시도가 끝날 때마다 덧붙이므로 중간에 멈춰도 앞의 기록은 남는다."""

    def __init__(self, path, run_id):
        self.path = path
        self.run_id = run_id
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event, **fields):
        record = {"ts": datetime.now().isoformat(timespec="seconds"), "run_id": self.run_id, "event": event}
        record.update(fields)
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def say(message):
    print(f"[loop] {message}", flush=True)


# ---------------------------------------------------------------- git

def git(*args, check=True):
    result = subprocess.run(["git", "-c", "core.quotepath=false", *args],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout


def changed_files():
    """작업 트리에서 바뀐 파일의 (상태, 경로) 목록. 루프가 쓰는 기록과 보고서 폴더는 뺀다."""
    changes = []
    for line in git("status", "--porcelain=v1", "--untracked-files=all").splitlines():
        status, path = line[:2], line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if not path.startswith(EXCLUDED):
            changes.append((status, path))
    return changes


def restore(changes):
    """마지막 커밋(체크포인트)의 상태로 되돌린다. 에이전트가 새로 만든 파일은 지운다."""
    git("restore", "--source=HEAD", "--staged", "--worktree", "--", ".")
    for status, path in changes:
        if status == "??":
            Path(path).unlink(missing_ok=True)


def save_diff(path, changes):
    """되돌리기 전에 그 시도의 변경을 파일로 남긴다. 버린 시도도 사람이 나중에 볼 수 있게 한다."""
    text = git("diff", "HEAD", "--", ".")
    created = [p for status, p in changes if status == "??"]
    if created:
        text += "\n# 새로 만든 파일(되돌릴 때 지움): " + ", ".join(created) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path.as_posix()


def commit(changes, message):
    git("add", "-A", "--", *[path for _, path in changes])
    git("commit", "-q", "-m", message)
    return git("rev-parse", "--short", "HEAD").strip()


# ---------------------------------------------------------------- 판정

def judge(config):
    """판정 명령을 실행해 (종료 코드, 출력)을 돌려준다. pytest 종료 코드: 0 통과, 1 실패, 5 수집 없음."""
    result = subprocess.run(shlex.split(config.judge_cmd), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    return result.returncode, result.stdout + result.stderr


def count_failures(code, output):
    """실패와 오류의 개수. 통과면 0, 개수를 읽지 못하면 999(가장 나쁨)로 본다."""
    if code == 0:
        return 0
    found = SUMMARY_PATTERN.findall(output)
    return sum(int(number) for number, _ in found) if found else 999


def summarize_failures(output, limit=2000):
    """다음 시도에 넘길 실패 출력의 요약: FAILED·ERROR 줄과 E 줄을 앞에서부터, 길이 상한까지."""
    keep = [line.rstrip() for line in output.splitlines()
            if line.startswith(("FAILED ", "ERROR ", "E ")) or "Error while" in line]
    text = "\n".join(keep) if keep else "\n".join(output.strip().splitlines()[-20:])
    if len(text) > limit:
        text = text[:limit] + "\n…(줄임)"
    return text


def is_protected(path, protected):
    for item in protected:
        if item.endswith("/"):
            if path.startswith(item):
                return True
        elif path == item or path.endswith("/" + item):
            return True
    return False


def protected_changes(changes, protected):
    """바뀐 파일 가운데 보호 경로에 든 것의 목록. 하나라도 있으면 그 시도는 버린다(테스트 회피 막기).

    TODO(실습 6절): 지금은 언제나 빈 목록을 돌려주므로, 에이전트가 테스트를 고쳐 통과시켜도
    루프가 알아채지 못한다. is_protected()를 써서 보호 경로에 든 경로만 골라 돌려주게 고친다.
    고친 뒤 `python -m pytest -q ops/loop/tests`의 test_cheat_attempt_is_rejected가 통과해야 한다.
    """
    return []


# ---------------------------------------------------------------- 실행

def build_prompt(config, attempt, failures, history):
    template = (HERE / "prompt_fix.md").read_text(encoding="utf-8")
    values = {
        "RUN_ID": config.run_id, "ATTEMPT": str(attempt), "MAX_ATTEMPTS": str(config.max_attempts),
        "PROTECTED": ", ".join(f"`{p}`" for p in config.protected),
        "FAILURES": failures or "(없음)", "HISTORY": "\n".join(history) or "(첫 시도)",
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def run_agent(config, prompt, attempt, run_budget):
    """에이전트를 한 번 실행하고 결과 JSON에서 비용과 상태를 읽는다."""
    command = shlex.split(config.agent_cmd) + [
        "-p", prompt,
        "--output-format", "json",
        "--append-system-prompt", APPEND_PROMPT,
        "--allowedTools", ",".join(ALLOWED_TOOLS),
        "--disallowedTools", ",".join(DENIED_TOOLS),
        "--permission-mode", "dontAsk",
        "--max-turns", str(config.max_turns),
        "--max-budget-usd", f"{run_budget:.2f}",
    ]
    env = dict(os.environ, LOOP_ATTEMPT=str(attempt), LOOP_RUN_ID=config.run_id)
    # 에이전트가 부르는 python이 루프와 같은 가상 환경의 것이 되도록 한다.
    # 가상 환경의 실행 파일 폴더(Windows .venv/Scripts, macOS .venv/bin)를 PATH 맨 앞에 넣는다.
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    # 파이썬으로 된 에이전트(가짜 에이전트)가 Windows에서도 UTF-8로 출력하게 한다(부록 A-4-4).
    env.setdefault("PYTHONUTF8", "1")
    info = {"agent_exit": None, "agent_status": "ok", "subtype": None, "cost_usd": None,
            "turns": None, "session_id": None, "agent_result": None}
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", stdin=subprocess.DEVNULL,
                                timeout=config.attempt_timeout, env=env)
    except subprocess.TimeoutExpired:
        info["agent_status"] = "timeout"
    else:
        info["agent_exit"] = result.returncode
        try:
            data = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            info["agent_status"] = "no_json"
            info["agent_result"] = (result.stdout + result.stderr).strip()[-300:]
        else:
            info["subtype"] = data.get("subtype")
            info["cost_usd"] = data.get("total_cost_usd")
            info["turns"] = data.get("num_turns")
            info["session_id"] = data.get("session_id")
            info["agent_result"] = (data.get("result") or "")[-300:]
            if data.get("is_error"):
                info["agent_status"] = "error"
    info["agent_seconds"] = round(time.monotonic() - started, 1)
    # 비용을 알 수 없으면 그 시도의 상한을 모두 쓴 것으로 센다(보수적으로 센다).
    info["cost_counted"] = info["cost_usd"] if isinstance(info["cost_usd"], (int, float)) else run_budget
    return info


# ---------------------------------------------------------------- 보고서

def write_report(root, config, status, attempts, spent, failures, start_commit, branch):
    reasons = {
        "gave_up": f"재시도 상한({config.max_attempts}회)에 닿았다",
        "budget": f"비용 상한({config.budget:.2f}달러)에 닿았다",
        "time": f"시간 상한({config.max_seconds:.0f}초)에 닿았다",
        "suspicious": "판정 명령이 테스트를 하나도 수집하지 못하였다(테스트 회피 의심)",
        "precondition": "시도 중에 에이전트를 실행하지 못하였다",
    }
    rows = ["| 시도 | 에이전트 | 비용(달러) | 바꾼 파일 | 판정 | 실패 수 | 처리 |", "|---|---|---|---|---|---|---|"]
    for a in attempts:
        cost = "-" if a["cost_usd"] is None else f"{a['cost_usd']:.2f}"
        files = ", ".join(a["changed"]) or "없음"
        judge_code = "-" if a["judge_exit"] is None else a["judge_exit"]
        rows.append(f"| {a['attempt']} | {a['subtype'] or a['agent_status']} | {cost} | {files} | "
                    f"{judge_code} | {a['failures'] if a['failures'] is not None else '-'} | {a['decision']} |")
    head = git("rev-parse", "--short", "HEAD").strip()
    text = f"""# 루프 보고서: {config.run_id}

- 결과: **사람의 확인이 필요하다.** {reasons.get(status, status)}.
- 시도: {len(attempts)}회, 쓴 비용(셈한 값): {spent:.2f}달러 / 상한 {config.budget:.2f}달러
- 시작 커밋: `{start_commit}`, 루프 브랜치: `{branch}`, 지금 HEAD: `{head}`
- 작업 트리: 마지막 체크포인트 상태로 되돌려 두었다. 진전이 없던 시도의 변경은 남아 있지 않다.

## 시도별 기록

{chr(10).join(rows)}

## 마지막 판정의 실패 출력 (요약)

```text
{failures}
```

## 사람에게 묻는 것

1. 실패 출력이 가리키는 원인이 제품 코드에 있는가, 테스트나 환경에 있는가.
2. 루프 브랜치의 체크포인트 커밋을 살릴 것인가, 버릴 것인가: `git log --oneline {start_commit}..{branch}`
3. 다시 돌린다면 무엇을 바꿀 것인가: 지시문(`ops/loop/prompt_fix.md`), 상한, 허용 도구.

## 이슈로 올릴 때

보고서를 검토한 뒤 사람이 올린다. 루프는 이슈를 직접 만들지 않는다.

```bash
gh issue create --title "루프 {config.run_id}: {reasons.get(status, status)}" --body-file {REPORT_DIR}/{config.run_id}.md
```

자세한 기록: `{LOG_DIR}/{config.run_id}.jsonl`
"""
    path = root / REPORT_DIR / f"{config.run_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


# ---------------------------------------------------------------- 루프

def main():
    config = Config()
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        say("git 저장소 안에서 실행해야 한다.")
        return EXIT["precondition"]
    root = Path(top.stdout.strip())
    os.chdir(root)
    log = JsonlLog(root / LOG_DIR / f"{config.run_id}.jsonl", config.run_id)
    prompt_dir = root / LOG_DIR / config.run_id

    def finish(status, **fields):
        log.write("end", status=status, exit_code=EXIT[status], **fields)
        say(f"끝: {status} (종료 코드 {EXIT[status]})")
        return EXIT[status]

    log.write("start", config=config.as_dict())
    dirty = changed_files()
    if dirty:
        say("작업 트리에 커밋하지 않은 변경이 있다. 커밋하거나 치운 뒤 다시 실행한다.")
        return finish("precondition", reason="dirty", files=[p for _, p in dirty])

    started = time.monotonic()
    code, output = judge(config)
    best = count_failures(code, output)
    log.write("judge", attempt=0, judge_exit=code, failures=best)
    if code == 0:
        say("처음부터 통과한다. 할 일이 없다.")
        return finish("already_green")
    if code not in (1, 2, 4):
        say(f"판정 명령의 종료 코드가 {code}이다. 테스트 환경부터 확인한다.")
        return finish("precondition", reason=f"judge_exit_{code}")

    start_commit = git("rev-parse", "--short", "HEAD").strip()
    branch = f"loop/{config.run_id}"
    try:
        git("switch", "-q", "-c", branch)
    except RuntimeError as error:
        say(str(error))
        return finish("precondition", reason="branch")
    say(f"브랜치 {branch}에서 시작한다. 실패 {best}개.")
    failures = summarize_failures(output)
    history, attempts, spent, status = [], [], 0.0, "gave_up"

    for attempt in range(1, config.max_attempts + 1):
        remaining = config.budget - spent
        if time.monotonic() - started > config.max_seconds:
            status = "time"
            break
        if remaining < config.min_run_budget:
            status = "budget"
            break
        run_budget = min(config.run_budget, remaining)
        prompt = build_prompt(config, attempt, failures, history)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        (prompt_dir / f"attempt-{attempt}.prompt.md").write_text(prompt, encoding="utf-8", newline="\n")

        say(f"시도 {attempt}/{config.max_attempts}: 에이전트 실행 (이번 상한 {run_budget:.2f}달러)")
        try:
            info = run_agent(config, prompt, attempt, run_budget)
        except FileNotFoundError:
            say(f"에이전트 명령을 찾지 못하였다: {config.agent_cmd}")
            restore(changed_files())
            status = "precondition"
            break
        spent += info["cost_counted"]
        changes = changed_files()
        record = dict(attempt=attempt, **info, changed=[p for _, p in changes],
                      protected=[], judge_exit=None, failures=None, decision=None, commit=None, diff=None)

        diff_path = prompt_dir / f"attempt-{attempt}.diff"
        bad = protected_changes(changes, config.protected)
        if bad:
            record.update(diff=save_diff(diff_path.relative_to(root), changes))
            restore(changes)
            record.update(protected=bad, decision="reject")
            failures = (f"직전 시도가 보호 경로({', '.join(bad)})를 고쳐 통과시키려 하였다. 그 시도는 버렸다. "
                        f"보호 경로는 고치지 않는다.\n" + failures)
            history.append(f"- 시도 {attempt}: 보호 경로를 고쳐 버림({', '.join(bad)})")
        elif not changes:
            record.update(decision="no_change")
            history.append(f"- 시도 {attempt}: 아무 파일도 바꾸지 않음")
        else:
            code, output = judge(config)
            count = count_failures(code, output)
            record.update(judge_exit=code, failures=count)
            if code == 0:
                record.update(decision="commit", commit=commit(changes, f"fix: 루프 {config.run_id} 시도 {attempt} 통과"))
                status = "green"
            elif code == 5:
                record.update(diff=save_diff(diff_path.relative_to(root), changes))
                restore(changes)
                record.update(decision="restore")
                status = "suspicious"
            elif count < best:
                record.update(decision="checkpoint",
                              commit=commit(changes, f"fix: 루프 {config.run_id} 시도 {attempt} 진행(실패 {best}→{count})"))
                history.append(f"- 시도 {attempt}: 실패 {best}개 → {count}개, 진전이므로 커밋으로 남김")
                best = count
            else:
                record.update(diff=save_diff(diff_path.relative_to(root), changes))
                restore(changes)
                record.update(decision="restore")
                history.append(f"- 시도 {attempt}: 실패 {count}개(이전 {best}개), 진전이 없어 되돌림")
            if code != 0:
                failures = summarize_failures(output)
        attempts.append(record)
        log.write("attempt", **record, spent_usd=round(spent, 4))
        say(f"시도 {attempt}: {record['decision']} (판정 {record['judge_exit']}, 실패 {record['failures']}, "
            f"누적 비용 {spent:.2f}달러)")
        if status in ("green", "suspicious"):
            break

    fields = dict(attempts=len(attempts), spent_usd=round(spent, 4), branch=branch, start_commit=start_commit)
    if status == "green":
        say(f"통과. 검토 뒤 병합한다: git diff {start_commit}..{branch}")
        return finish("green", **fields)
    report = write_report(root, config, status, attempts, spent, failures, start_commit, branch)
    say(f"멈춤. 보고서: {report.relative_to(root).as_posix()}")
    return finish(status, report=report.relative_to(root).as_posix(), **fields)


if __name__ == "__main__":
    sys.exit(main())
