"""perm_sim.py의 테스트: 문서의 판정 규칙을 옮긴 모의기가 문서의 예와 같은 답을 내는가."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from globmatch import matches  # noqa: E402
from perm_sim import bash_matches, judge, load_settings, split_compound  # noqa: E402


def settings(tmp_path, **lists):
    path = tmp_path / f"s{len(list(tmp_path.iterdir()))}.json"
    path.write_text(json.dumps({"permissions": lists}), encoding="utf-8")
    return path


# 문서 「Wildcard patterns」 표의 예
@pytest.mark.parametrize("spec, command, expected", [
    ("npm run build", "npm run build", True),
    ("npm run build", "npm run build --watch", False),
    ("npm run *", "npm run test --watch", True),
    ("npm run *", "npm run", True),
    ("npm run *", "npm install", False),
    ("git log * main", "git log --oneline main", True),
    ("git log * main", "git log main", False),
    ("ls *", "ls -la", True),
    ("ls *", "lsof", False),
    ("ls*", "lsof", True),
    ("ls:*", "ls -la", True),
    ("* --help *", "npm --help", False),
])
def test_bash_wildcards_follow_documented_examples(spec, command, expected):
    assert bash_matches(spec, command) is expected


def test_split_compound_respects_quotes():
    assert split_compound('git commit -m "a && b" && git push') == ['git commit -m "a && b"', "git push"]
    assert split_compound("ls | wc -l; pwd") == ["ls", "wc -l", "pwd"]


@pytest.mark.parametrize("pattern, path, expected", [
    ("./.env", ".env", True),
    ("./.env", "api/.env", False),
    (".env", "api/.env", True),
    ("api/**/*.py", "api/main.py", True),
    ("api/**/*.py", "api/sub/x.py", True),
    ("api/**/*.py", "rag/x.py", False),
    ("src/**/*.{ts,tsx}", "src/a/b.tsx", True),
    ("/*.md", "README.md", True),
    ("/*.md", "docs/a.md", False),
])
def test_glob_patterns(pattern, path, expected):
    assert matches(pattern, path) is expected


def test_deny_wins_over_ask_and_allow(tmp_path):
    f = settings(tmp_path, allow=["Bash(git push *)"], ask=["Bash(git push *)"], deny=["Bash(git push --force *)"])
    sources = load_settings([f])
    assert judge(sources, "Bash(git push origin main)")[0] == "ask"
    assert judge(sources, "Bash(git push --force origin main)")[0] == "deny"


def test_lists_merge_across_files_and_deny_anywhere_wins(tmp_path):
    user = settings(tmp_path, allow=["Read(./.env)"])
    project = settings(tmp_path, deny=["Read(./.env)"])
    assert judge(load_settings([user, project]), "Read(.env)")[0] == "deny"
    assert judge(load_settings([project, user]), "Read(.env)")[0] == "deny"


def test_compound_command_needs_every_part_allowed(tmp_path):
    sources = load_settings([settings(tmp_path, allow=["Bash(npm test)"])])
    assert judge(sources, "Bash(npm test)")[0] == "allow"
    assert judge(sources, "Bash(npm test && rm -rf build)")[0] == "ask"
    assert judge(sources, "Bash(git status && npm test)")[0] == "allow"  # git status는 읽기 전용


def test_read_deny_covers_cat_and_edit_but_not_python(tmp_path):
    sources = load_settings([settings(tmp_path, deny=["Read(./.env)"])])
    assert judge(sources, "Bash(cat .env)")[0] == "deny"
    assert judge(sources, "Edit(.env)")[0] == "deny"
    assert judge(sources, "Bash(python -c \"open('.env')\")")[0] == "ask"


def test_negation_carves_out_of_earlier_rule(tmp_path):
    sources = load_settings([settings(tmp_path, deny=["Read(./.env.*)", "Read(!.env.example)"])])
    assert judge(sources, "Read(.env.local)")[0] == "deny"
    assert judge(sources, "Read(.env.example)")[0] == "allow"


def test_negation_listed_first_carves_nothing(tmp_path):
    sources = load_settings([settings(tmp_path, deny=["Read(!.env.example)", "Read(./.env.*)"])])
    assert judge(sources, "Read(.env.example)")[0] == "deny"


def test_deny_single_directory_pattern_matches_any_depth(tmp_path):
    deny = load_settings([settings(tmp_path, deny=["Edit(src/**)"])])
    allow = load_settings([settings(tmp_path, allow=["Edit(src/**)"])])
    assert judge(deny, "Edit(vendor/pkg/src/lib.js)")[0] == "deny"
    assert judge(allow, "Edit(vendor/pkg/src/lib.js)")[0] == "ask"  # allow는 그 위치에서만 맞는다
    assert judge(allow, "Edit(src/app.ts)")[0] == "allow"


def test_protected_paths_still_ask_even_with_allow(tmp_path):
    sources = load_settings([settings(tmp_path, allow=["Edit(./.claude/**)"])])
    assert judge(sources, "Edit(.claude/settings.json)")[0] == "ask"


def test_bare_tool_name_matches_every_use(tmp_path):
    sources = load_settings([settings(tmp_path, deny=["WebFetch"])])
    assert judge(sources, "WebFetch(domain:example.com)")[0] == "deny"


KIT = Path(__file__).resolve().parents[3]


def _check_cases(cases, sources):
    for line in cases.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            call, _, expected = line.partition("=>")
            assert judge(sources, call.strip())[0] == expected.strip(), call


def test_kit_merge_cases_have_no_mismatch():
    """견본/설정의 세 범위를 합친 판정(3-6절). 학생 키트에도 있는 파일만 쓴다."""
    k = KIT / "견본" / "설정"
    if not k.exists():  # 저장소에 복사한 뒤에는 키트가 옆에 없다
        pytest.skip("키트 폴더 밖(저장소의 ops/rules)에서는 견본이 없다")
    sources = load_settings([k / "user.json", k / "project.json", k / "local.json"])
    _check_cases(k / "판정사례_합치기.txt", sources)


@pytest.mark.skipif(not (KIT / "교수" / "완성본" / "settings.json").exists(),
                    reason="교수/가 없는 학생 키트이거나 저장소의 ops/rules이다")
def test_kit_cases_file_has_no_mismatch():
    cases = KIT / "견본" / "판정사례.txt"
    team = KIT / "교수" / "완성본" / "settings.json"
    sources = load_settings([team])
    _check_cases(cases, sources)
