"""ops/multi 조정 스크립트의 테스트.

jobprep 대신 작은 연습 저장소를 임시 폴더에 만들고, 그 안에서 스크립트를 실제로 실행한다.
구현 에이전트 자리에는 아래 AGENT_SOURCE의 작은 가짜 에이전트를 넣는다(모델을 부르지 않는다).

실행 (저장소 맨 위에서)
    python -m pytest -q ops/multi/tests
bash와 git이 필요하다. 저장소의 pytest.ini는 testpaths=tests이므로 기본 pytest -q에는 들어가지 않는다.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

MULTI = Path(__file__).resolve().parent.parent          # ops/multi
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash가 없다")

ISSUE = "ISSUE-01"
BASE = "feat/issue-01"

PLAN = """# ISSUE-01 계획서

- 이슈: 연습
- {approval}
- 통합 브랜치: `feat/issue-01`
"""
CARD = """# 작업 카드 ISSUE-01 {task}

- 소유 파일: `{owned}`, `docs/운영/인계/ISSUE-01/{task}_보고.md`
- 인수 테스트: `tests/test_{name}.py`
"""
# 가짜 에이전트: 지시문에서 작업을 읽어 calc/<a|b>.py의 값을 1로 바꾸고, 보고를 쓰고, 커밋한다.
# 환경 변수 SCN_<작업>: ok(기본), fail(값을 2로: 인수 테스트 실패), fail_once(첫 시도만 fail),
# scope(소유 밖 shared.md도 고침), test(기존 테스트를 고침), shared(소유한 shared.md의 첫 줄을 고침),
# append(공유 파일 log.md의 맨 끝에 한 줄을 더함), crash(아무것도 않고 종료 코드 1)
AGENT_SOURCE = r'''
import os, re, subprocess, sys
from pathlib import Path
prompt = sys.argv[-1]
m = re.search(r"인계/(ISSUE-\d+)/(T\d)_카드", prompt)
issue, task = m.group(1), m.group(2)
attempt = int(re.search(r"시도 (\d+)/", prompt).group(1))
scn = os.environ.get("SCN_" + task, "ok")
if scn == "crash":
    sys.exit(1)
name = {"T1": "a", "T2": "b"}[task]
value = 2 if scn == "fail" or (scn == "fail_once" and attempt == 1) else 1
files = [f"calc/{name}.py"]
Path(files[0]).write_text(f"{name.upper()} = {value}\n", encoding="utf-8")
if scn in ("scope", "shared"):
    Path("shared.md").write_text(f"첫 줄을 {task}가 고침\n둘째 줄\n", encoding="utf-8")
    files.append("shared.md")
if scn == "append":
    with open("log.md", "a", encoding="utf-8", newline="\n") as f:
        f.write(f"- {task} 끝\n")
    files.append("log.md")
if scn == "test":
    Path("tests/test_base.py").write_text("def test_base():\n    assert True  # 고침\n", encoding="utf-8")
    files.append("tests/test_base.py")
report = f"docs/운영/인계/{issue}/{task}_보고.md"
Path(report).write_text(f"# 결과 보고 {task}\n\n- 결과: 완료\n", encoding="utf-8")
subprocess.run(["git", "add", *files, report], check=True)
subprocess.run(["git", "commit", "-q", "-m", f"feat: {task}"], check=True)
print("done", task, attempt)
'''


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True,
                          text=True, encoding="utf-8")


def write(repo, path, text):
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8", newline="\n")


@pytest.fixture
def repo(tmp_path):
    """main에 기본 코드, feat/issue-01에 계획서·카드·인수 테스트가 있는 연습 저장소."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "tester")
    git(repo, "config", "user.email", "tester@example.invalid")
    git(repo, "config", "core.autocrlf", "false")
    shutil.copytree(MULTI, repo / "ops" / "multi",
                    ignore=shutil.ignore_patterns("tests", "logs", "__pycache__", "fake", "견본", "이슈"))
    write(repo, "calc/__init__.py", "")
    write(repo, "calc/a.py", "A = 0\n")
    write(repo, "calc/b.py", "B = 0\n")
    write(repo, "shared.md", "첫 줄\n둘째 줄\n")
    write(repo, "pytest.ini", "[pytest]\ntestpaths = tests\npythonpath = .\n")
    write(repo, "tests/test_base.py", "def test_base():\n    assert True\n")
    write(repo, ".gitignore", ".claude/worktrees/\n__pycache__/\n.pytest_cache/\n")
    write(repo, "agent.py", AGENT_SOURCE)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "chore: 시작")
    git(repo, "switch", "-q", "-c", BASE)
    write(repo, "docs/운영/인계/ISSUE-01/계획서.md", PLAN.format(approval="승인: 운영 책임자, 2027-11-16"))
    write(repo, "docs/운영/인계/ISSUE-01/T1_카드.md", CARD.format(task="T1", owned="calc/a.py", name="a"))
    write(repo, "docs/운영/인계/ISSUE-01/T2_카드.md", CARD.format(task="T2", owned="calc/b.py", name="b"))
    write(repo, "tests/test_a.py", "from calc.a import A\n\ndef test_a():\n    assert A == 1\n")
    write(repo, "tests/test_b.py", "from calc.b import B\n\ndef test_b():\n    assert B == 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "docs: 계획서와 인수 테스트")
    return repo


def run(repo, script, *args, **env):
    full_env = dict(os.environ)
    full_env.update({"MULTI_PY": sys.executable, "FAKE_DELAY": "0",
                     "AGENT_CMD": f"{Path(sys.executable).as_posix()} {(repo / 'agent.py').as_posix()}"})
    full_env.update(env)
    return subprocess.run([BASH, f"ops/multi/{script}", *args], cwd=repo, env=full_env,
                          capture_output=True, text=True, encoding="utf-8")


def events(repo):
    path = repo / "ops" / "multi" / "logs" / ISSUE / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def prepare_dispatch_judge(repo, **env):
    assert run(repo, "prepare.sh", ISSUE, "T1", "T2").returncode == 0
    assert run(repo, "dispatch.sh", ISSUE, "T1", "T2", **env).returncode == 0
    return run(repo, "judge.sh", ISSUE, "T1", **env), run(repo, "judge.sh", ISSUE, "T2", **env)


def test_prepare_refuses_without_approval(repo):
    write(repo, "docs/운영/인계/ISSUE-01/계획서.md", PLAN.format(approval="승인 대기"))
    git(repo, "commit", "-q", "-am", "docs: 승인 취소")
    result = run(repo, "prepare.sh", ISSUE, "T1")
    assert result.returncode == 2
    assert "승인" in result.stderr
    assert not (repo / ".claude" / "worktrees").exists()


def test_prepare_refuses_shared_ownership(repo):
    write(repo, "docs/운영/인계/ISSUE-01/T2_카드.md", CARD.format(task="T2", owned="calc/a.py", name="b"))
    git(repo, "commit", "-q", "-am", "docs: 카드 실수")
    result = run(repo, "prepare.sh", ISSUE, "T1", "T2")
    assert result.returncode == 2
    assert "calc/a.py" in result.stderr


def test_prepare_creates_worktrees_on_task_branches(repo):
    result = run(repo, "prepare.sh", ISSUE, "T1", "T2")
    assert result.returncode == 0, result.stderr
    listing = git(repo, "worktree", "list", "--porcelain").stdout
    assert "branch refs/heads/agent/issue-01-t1" in listing
    assert "branch refs/heads/agent/issue-01-t2" in listing
    assert (repo / ".claude/worktrees/issue-01-t1/calc/a.py").exists()
    # 같은 명령을 다시 실행해도 그대로 둔다
    again = run(repo, "prepare.sh", ISSUE, "T1", "T2")
    assert again.returncode == 0 and again.stdout.count("있음") == 2


def test_full_flow_parallel_judge_merge_cleanup(repo):
    j1, j2 = prepare_dispatch_judge(repo)
    assert j1.returncode == 0, j1.stdout
    assert j2.returncode == 0, j2.stdout
    merged = run(repo, "merge.sh", ISSUE, "T1", "T2")
    assert merged.returncode == 0, merged.stderr
    log = git(repo, "log", "--format=%s", "-3").stdout.splitlines()
    assert log[0] == "chore: ISSUE-01 T2 병합 (agent/issue-01-t2)"
    assert log[1].startswith("feat: T2") or log[1] == "chore: ISSUE-01 T1 병합 (agent/issue-01-t1)"
    assert (repo / "calc/a.py").read_text(encoding="utf-8") == "A = 1\n"
    assert (repo / "calc/b.py").read_text(encoding="utf-8") == "B = 1\n"
    status = run(repo, "status.sh", ISSUE)
    assert status.stdout.count("| 통과 | 예 |") == 2
    cleaned = run(repo, "cleanup.sh", ISSUE, "T1", "T2")
    assert cleaned.returncode == 0, cleaned.stderr
    assert "agent/issue-01" not in git(repo, "branch").stdout
    assert git(repo, "worktree", "list").stdout.count("\n") == 1
    kinds = [e["event"] for e in events(repo)]
    for kind in ("worktree_created", "dispatched", "finished", "judged", "merged", "cleaned"):
        assert kind in kinds


def test_dispatch_runs_agents_in_parallel(repo):
    assert run(repo, "prepare.sh", ISSUE, "T1", "T2").returncode == 0
    trace = repo / "trace.txt"
    slow_agent = repo / "slow_agent.sh"
    # 두 에이전트가 서로를 기다린다(최대 30초). 차례로 실행되면 첫 에이전트는 둘째를 만나지 못하고 timeout을 남긴다.
    t = trace.as_posix()
    slow_agent.write_text(
        f'echo start >> "{t}"\n'
        f'for i in $(seq 1 150); do [ "$(grep -c start "{t}")" -ge 2 ] && break; sleep 0.2; done\n'
        f'if [ "$(grep -c start "{t}")" -ge 2 ]; then echo end >> "{t}"; else echo timeout >> "{t}"; fi\n',
        encoding="utf-8")
    result = run(repo, "dispatch.sh", ISSUE, "T1", "T2", AGENT_CMD=f"bash {slow_agent.as_posix()}")
    assert result.returncode == 0
    assert sorted(trace.read_text(encoding="utf-8").split()) == ["end", "end", "start", "start"]
    finished = [e for e in events(repo) if e["event"] == "finished"]
    assert len(finished) == 2


def test_dispatch_requires_agent_cmd(repo):
    assert run(repo, "prepare.sh", ISSUE, "T1").returncode == 0
    result = run(repo, "dispatch.sh", ISSUE, "T1", AGENT_CMD="")
    assert result.returncode == 2


def test_judge_rejects_change_outside_owned_files(repo):
    j1, _ = prepare_dispatch_judge(repo, SCN_T1="scope")
    assert j1.returncode == 1
    verdict = (repo / "ops/multi/logs/ISSUE-01/판정_T1.md").read_text(encoding="utf-8")
    assert "- 판정: 거부" in verdict and "shared.md" in verdict


def test_judge_rejects_modified_existing_test(repo):
    j1, _ = prepare_dispatch_judge(repo, SCN_T1="test")
    assert j1.returncode == 1
    verdict = (repo / "ops/multi/logs/ISSUE-01/판정_T1.md").read_text(encoding="utf-8")
    assert "| 동결 | 거부 |" in verdict


def test_judge_rejects_failing_acceptance_test(repo):
    j1, j2 = prepare_dispatch_judge(repo, SCN_T2="fail")
    assert j1.returncode == 0
    assert j2.returncode == 1
    verdict = (repo / "ops/multi/logs/ISSUE-01/판정_T2.md").read_text(encoding="utf-8")
    assert "| 테스트 | 거부 |" in verdict
    archived = list((repo / "ops/multi/logs/ISSUE-01").glob("판정_T2_*.md"))
    assert len(archived) == 1                     # 커밋별 판정도 남는다


def test_judge_ignores_tests_of_other_unmerged_tasks(repo):
    j1, _ = prepare_dispatch_judge(repo, SCN_T2="fail")
    assert j1.returncode == 0     # T2의 인수 테스트(test_b.py)는 T1 판정에서 뺀다


def test_judge_ignores_tests_of_task_without_commits(repo):
    # 커밋이 하나도 없는 작업 브랜치는 git으로는 통합 브랜치의 「조상」이지만 병합된 것이 아니다
    assert run(repo, "prepare.sh", ISSUE, "T1", "T2").returncode == 0
    assert run(repo, "dispatch.sh", ISSUE, "T1", "T2", SCN_T2="crash").returncode == 1
    assert run(repo, "judge.sh", ISSUE, "T1").returncode == 0
    j2 = run(repo, "judge.sh", ISSUE, "T2")
    assert j2.returncode == 1
    verdict = (repo / "ops/multi/logs/ISSUE-01/판정_T2.md").read_text(encoding="utf-8")
    assert "| 범위 | 거부 | 바뀐 파일이 없다 |" in verdict
    assert run(repo, "cleanup.sh", ISSUE, "T2").returncode == 1


def test_merge_refuses_when_branch_moved_after_judgement(repo):
    prepare_dispatch_judge(repo)
    wt = repo / ".claude/worktrees/issue-01-t1"
    write(wt, "calc/a.py", "A = 1  # 판정 뒤에 고침\n")
    git(wt, "commit", "-q", "-am", "fix: 판정 뒤 커밋")
    result = run(repo, "merge.sh", ISSUE, "T1", "T2")
    assert result.returncode == 2
    assert "다시 판정" in result.stderr
    assert git(repo, "log", "-1", "--format=%s").stdout.strip() == "docs: 계획서와 인수 테스트"


def test_merge_conflict_is_aborted_and_reported(repo):
    write(repo, "docs/운영/인계/ISSUE-01/T2_카드.md",
          CARD.format(task="T2", owned="calc/b.py`, `shared.md", name="b"))
    git(repo, "commit", "-q", "-am", "docs: T2가 shared.md를 소유")
    j1, j2 = prepare_dispatch_judge(repo, SCN_T2="shared")
    assert j1.returncode == 0 and j2.returncode == 0, j2.stdout
    # 그사이 조정자가 통합 브랜치에서 같은 줄을 고쳤다
    write(repo, "shared.md", "첫 줄을 조정자가 고침\n둘째 줄\n")
    git(repo, "commit", "-q", "-am", "docs: 조정자의 수정")
    result = run(repo, "merge.sh", ISSUE, "T1", "T2")
    assert result.returncode == 3
    assert "shared.md" in result.stderr
    assert not (repo / ".git" / "MERGE_HEAD").exists()
    assert git(repo, "status", "--porcelain", "--untracked-files=no").stdout == ""
    assert git(repo, "log", "-1", "--format=%s").stdout.strip() == "chore: ISSUE-01 T1 병합 (agent/issue-01-t1)"


SHARED_LINE = "- 공유 파일: `log.md` (맨 끝에 한 줄만 더한다)\n"


def share_log(repo):
    """두 카드에 공유 파일 log.md를 더하고, 통합 브랜치에 log.md를 둔다."""
    for task, owned, name in (("T1", "calc/a.py", "a"), ("T2", "calc/b.py", "b")):
        write(repo, f"docs/운영/인계/ISSUE-01/{task}_카드.md", CARD.format(task=task, owned=owned, name=name) + SHARED_LINE)
    write(repo, "log.md", "# 기록\n\n- 시작\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "docs: 공유 파일 log.md")


def test_shared_file_is_reported_and_accepted_by_judge(repo):
    share_log(repo)
    prepared = run(repo, "prepare.sh", ISSUE, "T1", "T2")
    assert prepared.returncode == 0, prepared.stderr
    assert "공유  log.md: T1 T2" in prepared.stdout
    assert run(repo, "dispatch.sh", ISSUE, "T1", "T2", SCN_T1="append", SCN_T2="append").returncode == 0
    j1 = run(repo, "judge.sh", ISSUE, "T1")
    assert j1.returncode == 0, j1.stdout
    assert "공유 파일 1개 포함" in j1.stdout


def test_prepare_refuses_owned_file_listed_as_shared_by_other(repo):
    write(repo, "docs/운영/인계/ISSUE-01/T2_카드.md",
          CARD.format(task="T2", owned="calc/b.py", name="b") + "- 공유 파일: `calc/a.py`\n")
    git(repo, "commit", "-q", "-am", "docs: T2가 T1의 파일을 공유로 적음")
    result = run(repo, "prepare.sh", ISSUE, "T1", "T2")
    assert result.returncode == 2
    assert "calc/a.py는 T1의 소유 파일인데 T2가 공유 파일로 적었다" in result.stderr


def test_shared_file_conflict_is_resolved_in_task_worktree(repo):
    # 10장 핵심 실습의 흐름: 두 작업이 공유 파일 끝에 한 줄씩 더하면 뒤의 병합이 충돌한다.
    # 뒤 작업의 작업 공간에서 통합 브랜치를 받아 풀고, 다시 판정한 뒤 병합한다.
    share_log(repo)
    j1, j2 = prepare_dispatch_judge(repo, SCN_T1="append", SCN_T2="append")
    assert j1.returncode == 0 and j2.returncode == 0, j2.stdout
    first = run(repo, "merge.sh", ISSUE, "T1", "T2")
    assert first.returncode == 3
    assert "충돌  T2: log.md" in first.stderr
    wt = repo / ".claude/worktrees/issue-01-t2"
    assert git(wt, "merge", BASE, check=False).returncode != 0
    assert "<<<<<<<" in (wt / "log.md").read_text(encoding="utf-8")
    write(wt, "log.md", "# 기록\n\n- 시작\n- T1 끝\n- T2 끝\n")
    git(wt, "add", "log.md")
    git(wt, "commit", "-q", "--no-edit")
    stale = run(repo, "merge.sh", ISSUE, "T2")
    assert stale.returncode == 2 and "다시 판정한다" in stale.stderr
    assert run(repo, "judge.sh", ISSUE, "T2").returncode == 0
    second = run(repo, "merge.sh", ISSUE, "T2")
    assert second.returncode == 0, second.stderr
    assert (repo / "log.md").read_text(encoding="utf-8") == "# 기록\n\n- 시작\n- T1 끝\n- T2 끝\n"
    merged = [e["task"] for e in events(repo) if e["event"] == "merged"]
    assert merged == ["T1", "T2"]


def test_judge_finds_worktrees_made_elsewhere_by_branch(repo, tmp_path):
    # Orca처럼 다른 도구가 만든 작업 공간: 폴더 이름이 브랜치와 다르고, 두 작업 공간의 부모 폴더도 다르다.
    # MULTI_WT_BASE 없이 작업 브랜치 이름으로 찾아 판정하고 병합한다.
    wt1 = tmp_path / "도구A" / "space one"
    wt2 = tmp_path / "other-parent" / "ws_b"
    git(repo, "worktree", "add", "-q", "-b", "agent/issue-01-t1", str(wt1), BASE)
    git(repo, "worktree", "add", "-q", "-b", "agent/issue-01-t2", str(wt2), BASE)
    env = {"MULTI_WT_BASE": ""}
    assert run(repo, "dispatch.sh", ISSUE, "T1", "T2", **env).returncode == 0
    j1 = run(repo, "judge.sh", ISSUE, "T1", **env)
    j2 = run(repo, "judge.sh", ISSUE, "T2", **env)
    assert j1.returncode == 0 and j2.returncode == 0, j1.stdout + j1.stderr + j2.stdout + j2.stderr
    assert not (repo / ".claude" / "worktrees").exists()
    status = run(repo, "status.sh", ISSUE, **env)
    assert "space one" in status.stdout and "ws_b" in status.stdout
    assert run(repo, "merge.sh", ISSUE, "T1", "T2", **env).returncode == 0
    cleaned = run(repo, "cleanup.sh", ISSUE, "T1", "T2", **env)
    assert cleaned.returncode == 0, cleaned.stderr
    assert not wt1.exists() and not wt2.exists()


def test_merge_rolls_back_when_combined_tests_fail(repo):
    # 의미 충돌: 두 작업은 따로는 통과하지만 합치면 깨지는 규칙이 통합 브랜치에 있다
    write(repo, "tests/test_limit.py",
          "from calc.a import A\nfrom calc.b import B\n\ndef test_only_one_feature_on():\n    assert A + B < 2\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "test: 상한")
    prepare_dispatch_judge(repo)
    result = run(repo, "merge.sh", ISSUE, "T1", "T2")
    assert result.returncode == 4
    assert git(repo, "log", "-1", "--format=%s").stdout.strip() == "chore: ISSUE-01 T1 병합 (agent/issue-01-t1)"
    assert not (repo / ".git" / "MERGE_HEAD").exists()


def test_run_issue_retries_then_passes(repo):
    result = run(repo, "run_issue.sh", ISSUE, "T1", "T2", SCN_T2="fail_once")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "시도 2/3" in result.stdout
    dispatched = [e for e in events(repo) if e["event"] == "dispatched" and e["task"] == "T2"]
    assert len(dispatched) == 2


def test_run_issue_hands_over_after_max_attempts(repo):
    result = run(repo, "run_issue.sh", ISSUE, "T1", "T2", SCN_T2="fail", MULTI_MAX="2")
    assert result.returncode == 1
    assert "사람에게 넘긴다: T2" in result.stdout
    assert events(repo)[-1]["event"] == "handed_to_human"


def test_cleanup_keeps_unmerged_branch(repo):
    prepare_dispatch_judge(repo)
    result = run(repo, "cleanup.sh", ISSUE, "T1")
    assert result.returncode == 1
    assert (repo / ".claude/worktrees/issue-01-t1").exists()
    assert "agent/issue-01-t1" in git(repo, "branch").stdout


def test_check_agents_passes_on_repository_agents():
    root = MULTI.parent.parent                  # 저장소 맨 위
    result = subprocess.run([sys.executable, str(MULTI / "check_agents.py")], cwd=root,
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout
    assert "planner.md" in result.stdout and "implementer.md" in result.stdout


def test_check_agents_flags_unknown_field(tmp_path):
    write(tmp_path, ".claude/agents/helper.md",
          "---\nname: helper\ndescription: 돕는다\nallowed-tools: Read\nmodel: gpt\n---\n\n본문\n")
    result = subprocess.run([sys.executable, str(MULTI / "check_agents.py")], cwd=tmp_path,
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 1
    assert "allowed-tools" in result.stdout and "model 값 gpt" in result.stdout
