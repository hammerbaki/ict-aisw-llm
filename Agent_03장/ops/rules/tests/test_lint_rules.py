"""lint_rules.py의 테스트: 규칙 파일 자체의 검사."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lint_rules  # noqa: E402

GOOD_CLAUDE_MD = """# 예제
## 실행 명령
- 테스트: 가상 환경을 켠 뒤 python -m pytest -q ops/rules/tests
## 작업 규칙
- 테스트를 먼저 쓴다
## 금지
- .env를 읽지 않는다. 이유: 키가 들어 있다.
"""


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path, claude_md=GOOD_CLAUDE_MD, settings=None, gitignore=".claude/settings.local.json\nCLAUDE.local.md\n"):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "core.excludesFile", str(tmp_path / "없는파일"))  # 이 컴퓨터의 전역 제외를 쓰지 않는다
    (tmp_path / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "main.py").write_text("x = 1\n", encoding="utf-8")
    rules = tmp_path / ".claude" / "rules"
    rules.mkdir(parents=True)
    (rules / "api.md").write_text('---\npaths:\n  - "api/**/*.py"\n---\n- 규칙\n', encoding="utf-8")
    settings = settings if settings is not None else {"permissions": {"deny": ["Read(./.env)"]}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    (tmp_path / ".gitignore").write_text(gitignore, encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "pull_request_template.md").write_text("- [ ] 테스트\n", encoding="utf-8")
    (tmp_path / "docs" / "운영").mkdir(parents=True)
    (tmp_path / "docs" / "운영" / "저장소규약.md").write_text("# 규약\n", encoding="utf-8")
    (tmp_path / "CODEOWNERS").write_text("* @owner\n/.claude/ @owner\n", encoding="utf-8")
    return tmp_path


def run_lint(repo, capsys):
    code = lint_rules.main(["--repo", str(repo)])
    return code, capsys.readouterr().out


def test_complete_repo_passes(tmp_path, capsys):
    code, out = run_lint(make_repo(tmp_path), capsys)
    assert code == 0, out
    assert "실패 0건" in out


def test_forbidden_item_without_reason_fails(tmp_path, capsys):
    repo = make_repo(tmp_path, claude_md=GOOD_CLAUDE_MD.replace(" 이유: 키가 들어 있다.", ""))
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "이유:" in out


def test_long_claude_md_fails(tmp_path, capsys):
    repo = make_repo(tmp_path, claude_md=GOOD_CLAUDE_MD + "- 줄\n" * 200)
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "줄이다" in out


def test_rule_pattern_matching_no_file_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / ".claude" / "rules" / "web.md").write_text('---\npaths:\n  - "frontend/**"\n---\n- 규칙\n',
                                                      encoding="utf-8")
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "frontend/**" in out


def test_rule_without_front_matter_is_a_warning(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / ".claude" / "rules" / "all.md").write_text("- 머리말 없는 규칙\n", encoding="utf-8")
    code, out = run_lint(repo, capsys)
    assert code == 0
    assert "매 세션 읽힌다" in out


def test_broken_json_fails_with_position(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / ".claude" / "settings.json").write_text('{"permissions": {"deny": ["Read(./.env)",]}}',
                                                   encoding="utf-8")
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "JSON 문법 오류" in out


def test_settings_without_env_deny_fails(tmp_path, capsys):
    code, out = run_lint(make_repo(tmp_path, settings={"permissions": {"allow": ["Bash(npm test)"]}}), capsys)
    assert code == 1
    assert ".env 읽기를 거부하는 규칙이 없다" in out


def test_settings_warnings(tmp_path, capsys):
    settings = {"permissions": {"deny": ["Read(./.env)", "Write(./data/**)"], "alow": [],
                                "allow": ["Bash(git * main)"]}}
    code, out = run_lint(make_repo(tmp_path, settings=settings), capsys)
    assert code == 0
    assert "permissions.alow" in out
    assert "Edit 또는 Read" in out
    assert "별표 뒤에" in out


def test_project_default_mode_bypass_fails(tmp_path, capsys):
    settings = {"permissions": {"deny": ["Read(./.env)"], "defaultMode": "bypassPermissions"}}
    code, out = run_lint(make_repo(tmp_path, settings=settings), capsys)
    assert code == 1


def test_personal_files_must_be_ignored_by_repository(tmp_path, capsys):
    code, out = run_lint(make_repo(tmp_path, gitignore=""), capsys)
    assert code == 1
    assert "settings.local.json이(가) .gitignore에 없다" in out


def test_tracked_personal_file_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / "CLAUDE.local.md").write_text("개인 메모\n", encoding="utf-8")
    git(repo, "add", "-f", "CLAUDE.local.md")
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "git rm --cached" in out


def test_codeowners_negation_and_missing_owner(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / "CODEOWNERS").write_text("!/docs/ @owner\n/api/ @owner\n", encoding="utf-8")
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "'!'와 '[ ]'" in out
    assert "CLAUDE.md에 소유자가 없다" in out


def test_codeowners_last_match_wins():
    lines = [("*", ["@a"]), ("/.claude/", ["@b"])]
    assert lint_rules.owners_of(lines, ".claude/settings.json") == ["@b"]
    assert lint_rules.owners_of(lines, "CLAUDE.md") == ["@a"]


def test_placeholder_left_in_claude_md_fails(tmp_path, capsys):
    repo = make_repo(tmp_path, claude_md=GOOD_CLAUDE_MD + "- 「모델 이름에 관한 규칙」\n")
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "자리 표시" in out


def test_unquoted_glob_starting_with_star_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / ".claude" / "rules" / "py.md").write_text("---\npaths: **/*.py\n---\n- 규칙\n", encoding="utf-8")
    code, out = run_lint(repo, capsys)
    assert code == 1
    assert "따옴표로 감싼다" in out
