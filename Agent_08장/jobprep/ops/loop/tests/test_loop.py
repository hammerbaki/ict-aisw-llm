"""fix_until_green.py의 테스트. 모델을 부르지 않는다.

임시 폴더에 작은 저장소(calc.py와 그 테스트, 버그 두 개)를 만들고, 가짜 에이전트(fake_agent.py)를
에이전트 명령 자리에 끼워 루프를 실제로 실행한다. 루프의 종료 코드, 기록(JSONL), 보고서, git 상태를 확인한다.

실행 (저장소 맨 위에서): python -m pytest -q ops/loop/tests
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

LOOP_DIR = Path(__file__).resolve().parents[1]
FIX = LOOP_DIR / "fix_until_green.py"
FAKE = LOOP_DIR / "fake_agent.py"
PY = Path(sys.executable).as_posix()

sys.path.insert(0, str(LOOP_DIR))
import fix_until_green as loop  # noqa: E402

BUGGY = '''def add(a, b):
    return a - b


def is_adult(age):
    return age > 19
'''
TESTS = '''from calc import add, is_adult


def test_add():
    assert add(2, 3) == 5


def test_is_adult_at_19():
    assert is_adult(19) is True
'''
FIX_ADD = {"file": "calc.py", "old": "return a - b", "new": "return a + b"}
FIX_ADULT = {"file": "calc.py", "old": "return age > 19", "new": "return age >= 19"}


def git(repo, *args):
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=repo, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


@pytest.fixture
def repo(tmp_path):
    """버그 두 개가 있는 작은 저장소. 첫 커밋만 있고 작업 트리는 깨끗하다."""
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "calc.py").write_text(BUGGY, encoding="utf-8", newline="\n")
    (root / "tests" / "test_calc.py").write_text(TESTS, encoding="utf-8", newline="\n")
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\npythonpath = .\n", encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "test")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "core.autocrlf", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    return root


def scenario(tmp_path, attempts):
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps({"attempts": attempts}, ensure_ascii=False), encoding="utf-8")
    return path


def run_loop(repo, scenario_path, run_id="t1", **env):
    full_env = dict(os.environ, AGENT_CMD=f'"{PY}" "{FAKE.as_posix()}"', FAKE_SCENARIO=str(scenario_path),
                    LOOP_RUN_ID=run_id, PYTHONIOENCODING="utf-8")
    full_env.update({key: str(value) for key, value in env.items()})
    return subprocess.run([sys.executable, str(FIX)], cwd=repo, env=full_env, capture_output=True,
                          text=True, encoding="utf-8")


def read_log(repo, run_id="t1"):
    lines = (repo / "ops/loop/logs" / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def events(records, name):
    return [r for r in records if r["event"] == name]


# ------------------------------------------------------------- 세 경로: 성공, 3회 실패, 비용 상한

def test_success_path_commits_checkpoint_then_green(repo, tmp_path):
    path = scenario(tmp_path, [{"edits": [FIX_ADD], "cost_usd": 0.1}, {"edits": [FIX_ADULT], "cost_usd": 0.1}])
    result = run_loop(repo, path)
    assert result.returncode == 0, result.stdout + result.stderr
    records = read_log(repo)
    assert [a["decision"] for a in events(records, "attempt")] == ["checkpoint", "commit"]
    assert events(records, "end")[0]["status"] == "green"
    assert git(repo, "branch", "--show-current").strip() == "loop/t1"
    messages = git(repo, "log", "--format=%s").splitlines()
    assert messages[:2] == ["fix: 루프 t1 시도 2 통과", "fix: 루프 t1 시도 1 진행(실패 2→1)"]
    assert "return a + b" in (repo / "calc.py").read_text(encoding="utf-8")


def test_gives_up_after_three_attempts_and_writes_report(repo, tmp_path):
    wrong = {"file": "calc.py", "old": "def add(a, b):", "new": "def add(a, b):  # 고쳤다고 주장"}
    broken = {"file": "calc.py", "old": "def add(a, b):", "new": "def add(a, b)"}
    path = scenario(tmp_path, [{"edits": []}, {"edits": [wrong]}, {"edits": [broken]}])
    start = git(repo, "rev-parse", "HEAD")
    result = run_loop(repo, path)
    assert result.returncode == 1
    records = read_log(repo)
    assert len(events(records, "attempt")) == 3
    assert events(records, "end")[0]["status"] == "gave_up"
    report = (repo / "ops/loop/reports/t1.md").read_text(encoding="utf-8")
    assert "재시도 상한(3회)" in report and "| 3 |" in report
    # 진전이 없던 시도는 모두 되돌렸다: 커밋도 변경도 남지 않는다
    assert git(repo, "rev-parse", "HEAD") == start
    assert git(repo, "status", "--porcelain", "--", "calc.py", "tests") == ""
    assert (repo / "calc.py").read_text(encoding="utf-8") == BUGGY
    # 버린 시도의 변경은 diff 파일로 남는다
    diff = (repo / "ops/loop/logs/t1/attempt-2.diff").read_text(encoding="utf-8")
    assert "고쳤다고 주장" in diff
    assert events(records, "attempt")[1]["diff"] == "ops/loop/logs/t1/attempt-2.diff"


def test_budget_limit_stops_before_next_attempt(repo, tmp_path):
    path = scenario(tmp_path, [{"edits": [], "cost_usd": 0.45},
                               {"edits": [FIX_ADD], "cost_usd": 0.70, "overshoot_usd": 0.03},
                               {"edits": [FIX_ADD, FIX_ADULT], "cost_usd": 0.1}])
    result = run_loop(repo, path)
    assert result.returncode == 3
    records = read_log(repo)
    attempts = events(records, "attempt")
    assert len(attempts) == 2
    assert attempts[1]["subtype"] == "error_max_budget_usd"
    assert attempts[1]["cost_usd"] == pytest.approx(0.53)  # 상한 0.50을 응답 하나만큼 넘었다
    assert events(records, "end")[0]["status"] == "budget"
    assert (repo / "ops/loop/reports/t1.md").exists()


# ------------------------------------------------------------- 되돌림과 재시도의 세부

def test_failure_output_is_passed_to_next_attempt(repo, tmp_path):
    path = scenario(tmp_path, [{"edits": [FIX_ADD]}, {"edits": [FIX_ADULT]}])
    run_loop(repo, path)
    second = (repo / "ops/loop/logs/t1/attempt-2.prompt.md").read_text(encoding="utf-8")
    assert "test_is_adult_at_19" in second          # 시도 1 뒤에 남은 실패의 이름
    assert "test_add" not in second.split("## 앞선 시도")[0].split("실패 출력")[1]  # 고쳐진 것은 빠진다
    assert "실패 2개 → 1개" in second               # 앞선 시도의 처리 기록


def test_unknown_cost_is_counted_as_run_budget(repo, tmp_path):
    no_json = tmp_path / "no_json_agent.py"
    no_json.write_text("print('json이 아닌 출력')\n", encoding="utf-8")
    result = run_loop(repo, tmp_path / "unused.json", AGENT_CMD=f'"{PY}" "{no_json.as_posix()}"',
                      LOOP_MAX_ATTEMPTS=1, LOOP_RUN_BUDGET_USD=0.3)
    assert result.returncode == 1
    attempt = events(read_log(repo), "attempt")[0]
    assert attempt["agent_status"] == "no_json"
    assert attempt["cost_counted"] == pytest.approx(0.3)


def test_attempt_timeout_is_recorded(repo, tmp_path):
    path = scenario(tmp_path, [{"edits": [], "sleep_s": 5}])
    result = run_loop(repo, path, LOOP_MAX_ATTEMPTS=1, LOOP_ATTEMPT_TIMEOUT=1)
    assert result.returncode == 1
    assert events(read_log(repo), "attempt")[0]["agent_status"] == "timeout"


def test_cheat_attempt_is_rejected(repo, tmp_path):
    """테스트를 고쳐 통과시키는 시도는 버려야 한다(실습 6절의 TODO를 마치면 통과한다)."""
    cheat = {"file": "tests/test_calc.py", "old": "assert add(2, 3) == 5", "new": "assert add(2, 3) == -1"}
    cheat2 = {"file": "tests/test_calc.py", "old": "assert is_adult(19) is True", "new": "assert is_adult(19) is False"}
    path = scenario(tmp_path, [{"edits": [cheat, cheat2]}, {"edits": [FIX_ADD, FIX_ADULT]}])
    result = run_loop(repo, path)
    assert result.returncode == 0
    attempts = events(read_log(repo), "attempt")
    assert attempts[0]["decision"] == "reject"
    assert attempts[0]["protected"] == ["tests/test_calc.py"]
    assert (repo / "tests/test_calc.py").read_text(encoding="utf-8") == TESTS


# ------------------------------------------------------------- 시작 조건

def test_dirty_tree_is_refused(repo, tmp_path):
    (repo / "calc.py").write_text(BUGGY + "\n# 커밋하지 않은 변경\n", encoding="utf-8")
    result = run_loop(repo, scenario(tmp_path, []))
    assert result.returncode == 2
    assert git(repo, "branch", "--show-current").strip() == "main"


def test_already_green_does_nothing(repo, tmp_path):
    (repo / "calc.py").write_text(BUGGY.replace("a - b", "a + b").replace("> 19", ">= 19"), encoding="utf-8")
    git(repo, "commit", "-qam", "fixed by hand")
    result = run_loop(repo, scenario(tmp_path, []))
    assert result.returncode == 0
    assert events(read_log(repo), "end")[0]["status"] == "already_green"
    assert git(repo, "branch", "--show-current").strip() == "main"


def test_missing_agent_command_stops(repo, tmp_path):
    result = run_loop(repo, scenario(tmp_path, []), AGENT_CMD="no-such-agent-command")
    assert result.returncode == 2


def test_log_is_json_lines(repo, tmp_path):
    run_loop(repo, scenario(tmp_path, [{"edits": [FIX_ADD, FIX_ADULT]}]))
    text = (repo / "ops/loop/logs/t1.jsonl").read_text(encoding="utf-8")
    assert text.endswith("\n")
    for line in text.splitlines():
        record = json.loads(line)
        assert {"ts", "run_id", "event"} <= record.keys()


# ------------------------------------------------------------- 함수 단위

@pytest.mark.parametrize("code, output, expected", [
    (0, "5 passed in 0.1s", 0),
    (1, "2 failed, 41 passed in 2.0s", 2),
    (1, "1 failed, 3 passed, 1 error in 0.3s", 2),
    (2, "Interrupted: 1 error during collection", 1),
    (4, "ImportError while loading conftest", 999),
])
def test_count_failures(code, output, expected):
    assert loop.count_failures(code, output) == expected


def test_summarize_failures_keeps_key_lines_and_limits_length():
    output = "\n".join(["....F", "E   assert 1 == 2", "FAILED tests/test_x.py::test_y - assert 1 == 2"]
                       + [f"E   line {i}" for i in range(500)])
    text = loop.summarize_failures(output, limit=300)
    assert text.startswith("E   assert 1 == 2")
    assert "FAILED tests/test_x.py::test_y" in text
    assert len(text) <= 300 + len("\n…(줄임)")


@pytest.mark.parametrize("path, expected", [
    ("tests/test_calc.py", True), ("pytest.ini", True), ("api/conftest.py", True),
    (".claude/settings.json", True), ("calc.py", False), ("api/tests_helper.py", False),
])
def test_is_protected(path, expected):
    assert loop.is_protected(path, ["tests/", "pytest.ini", "conftest.py", ".claude/"]) is expected
