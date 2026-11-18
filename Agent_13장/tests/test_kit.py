"""13장 키트 도구의 테스트: 버전 고정 검사, 릴리스 본문 뽑기, 비밀 정보 검사, 코드 규칙 검사, 키트의 워크플로.

키트 폴더에서 실행한다:  python -m pytest -q tests
도구마다 임시 git 저장소를 만들어 통과하는 경우와 걸리는 경우를 하나씩 이상 확인한다.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parent.parent
SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
HASH = "    --hash=sha256:" + "0" * 64


def run(repo, script, *args):
    # Windows에서 PYTHONUTF8(부록 A-4-4)을 켜지 않았어도 도구의 한글 출력을 UTF-8로 받는다
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(repo / script), *args], cwd=repo, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def git_repo(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def install(repo, kit_path, repo_path):
    target = repo / repo_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(KIT / kit_path, target)


PINNED = {
    ".github/workflows/ci.yml": (
        "jobs:\n  t:\n    steps:\n"
        f"      - uses: actions/checkout@{SHA} # v7.0.1\n"
        "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0\n"
        "        with:\n          python-version-file: .python-version\n"
    ),
    "requirements.txt": "fastapi==0.163.2\n",
    "requirements.lock": f"fastapi==0.163.2 \\\n{HASH}\n    # via -r requirements.txt\n",
    ".python-version": "3.12\n",
    ".env.example": "LLM_MODEL=claude-haiku-5-5\nPROMPT_SUMMARY=summary_v1\nPROMPT_ASK=ask_v1\n",
}


def test_check_pins_passes_when_everything_is_pinned(tmp_path):
    repo = git_repo(tmp_path, PINNED)
    install(repo, "ops/version/check_pins.py", "ops/version/check_pins.py")
    result = run(repo, "ops/version/check_pins.py")
    assert result.returncode == 0, result.stdout
    assert "문제 0건" in result.stdout


@pytest.mark.parametrize("change, code", [
    ({".github/workflows/ci.yml": "steps:\n  - uses: actions/checkout@v7\n"}, "P1"),
    ({".github/workflows/ci.yml": f"steps:\n  - uses: actions/checkout@{SHA}\n"}, "P1"),
    ({"requirements.lock": "fastapi==0.163.2\n"}, "P2"),
    ({"requirements.txt": "fastapi==0.163.0\n"}, "P2"),
    ({".python-version": ""}, "P3"),
    ({".env.example": "LLM_MODEL=claude-haiku-latest\nPROMPT_SUMMARY=a\nPROMPT_ASK=b\n"}, "P4"),
    ({".env.example": "LLM_MODEL=m\nPROMPT_SUMMARY=\nPROMPT_ASK=b\n"}, "P5"),
])
def test_check_pins_finds_each_missing_pin(tmp_path, change, code):
    files = dict(PINNED)
    files.update(change)
    repo = git_repo(tmp_path, files)
    install(repo, "ops/version/check_pins.py", "ops/version/check_pins.py")
    result = run(repo, "ops/version/check_pins.py")
    assert result.returncode == 1
    assert result.stdout.splitlines()[0].startswith(code)


CHANGELOG = """# 변경 기록

## [Unreleased]

## [1.0.1] - 2027-12-08
### Fixed
- 검색어의 영문 대소문자를 가리지 않는다

## [1.0.0] - 2027-12-01
### Added
- 첫 릴리스
"""


def test_release_notes_extracts_one_section(tmp_path):
    repo = git_repo(tmp_path, {"CHANGELOG.md": CHANGELOG})
    install(repo, "ops/release/notes.py", "ops/release/notes.py")
    result = run(repo, "ops/release/notes.py", "v1.0.1")
    assert result.returncode == 0
    assert result.stdout.strip() == "### Fixed\n- 검색어의 영문 대소문자를 가리지 않는다"
    assert run(repo, "ops/release/notes.py", "v1.0.0").stdout.strip().endswith("첫 릴리스")


def test_release_notes_rejects_missing_or_malformed_version(tmp_path):
    repo = git_repo(tmp_path, {"CHANGELOG.md": CHANGELOG})
    install(repo, "ops/release/notes.py", "ops/release/notes.py")
    assert run(repo, "ops/release/notes.py", "v2.0.0").returncode == 1
    assert run(repo, "ops/release/notes.py", "release-1").returncode == 2


FAKE_KEY = "sk-ant-" + "api03-" + "x" * 40  # 글자 모양만 흉내 낸 가짜 값


SCANNER = ("security/scan_secrets.py", "security/tools/scan_secrets.py", "security/tools/secret_patterns.py")


def install_scanner(repo):
    """11장 키트의 비밀 정보 검사(입구와 본체)를 기준산출물에서 저장소로 복사한다."""
    for path in SCANNER:
        install(repo, f"기준산출물/{path}", path)


def test_scan_secrets_passes_clean_repo(tmp_path):
    repo = git_repo(tmp_path, {"README.md": "키는 .env에만 둔다\n", ".env.example": "ANTHROPIC_API_KEY=\n"})
    install_scanner(repo)
    result = run(repo, "security/scan_secrets.py")
    assert result.returncode == 0, result.stdout
    assert "찾지 못하였다" in result.stdout


def test_scan_secrets_finds_key_and_masks_it(tmp_path):
    repo = git_repo(tmp_path, {"api/config.py": f'KEY = "{FAKE_KEY}"\n', ".env.example": "ANTHROPIC_API_KEY=\n"})
    install_scanner(repo)
    result = run(repo, "security/scan_secrets.py")
    assert result.returncode == 1
    assert "발견  api/config.py:1  anthropic_api_key  sk-ant-a******" in result.stdout
    assert FAKE_KEY not in result.stdout  # 찾은 값을 그대로 출력하지 않는다


def test_scan_secrets_allowlist_uses_kind_names_of_chapter_11(tmp_path):
    repo = git_repo(tmp_path, {
        "security/재현/fake.txt": f"{FAKE_KEY}\n",
        "security/allowlist.txt": "# 11장 재현용 가짜 값\nsecurity/재현/fake.txt:anthropic_api_key\n",
    })
    install_scanner(repo)
    assert run(repo, "security/scan_secrets.py").returncode == 0
    # 11장의 종류 이름이 아닌 이름(예: anthropic-key)으로 적으면 예외가 되지 않는다
    (repo / "security/allowlist.txt").write_text("security/재현/fake.txt:anthropic-key\n", encoding="utf-8")
    assert run(repo, "security/scan_secrets.py").returncode == 1


MAP = """# 운영 요건 지도

| 요건 | 1장의 요건 | 장 | 산출물 | 확인 방법 | 자동화 | 남은 위험 |
|---|---|---|---|---|---|---|
| 보안 | OR-SEC-02 비밀 정보 | 11 | `security/scan_secrets.py` | `python security/scan_secrets.py` | CI | 모양이 다른 비밀 |
| 신뢰성 | OR-REL-08 테스트 | 2 | `tests/` | `pytest -q` | CI | 없음 |
| 일관성 | OR-CON-04 규칙 | 3 | `CLAUDE.md` | 읽기 | 수동 | 셀 수 없는 규칙 |
| 재현성 | OR-REP-02 고정 | 13 | `requirements.lock`, `.github/workflows/*.yml` | `check_pins.py` | CI | 환경에 묶임 |
"""
REQS = "| ID | 분류 |\n|---|---|\n| OR-SEC-02 | 보안 |\n| OR-REL-08 | 신뢰성 |\n| OR-CON-04 | 일관성 |\n| OR-REP-02 | 재현성 |\n"


def test_check_map(tmp_path):
    files = {"docs/운영/운영요건지도.md": MAP, "security/scan_secrets.py": "", "tests/x.py": "",
             "CLAUDE.md": "", "requirements.lock": "", ".github/workflows/ci.yml": ""}
    repo = git_repo(tmp_path, files)
    install(repo, "ops/map/check_map.py", "ops/map/check_map.py")
    result = run(repo, "ops/map/check_map.py")
    assert result.returncode == 0, result.stdout
    (repo / "CLAUDE.md").unlink()
    (repo / "docs/운영/운영요건지도.md").write_text(MAP.replace("| 수동 |", "| 「」 |"), encoding="utf-8")
    result = run(repo, "ops/map/check_map.py")
    assert result.returncode == 1
    assert "M2" in result.stdout and "`CLAUDE.md`" in result.stdout
    assert "M4" in result.stdout


def test_check_map_requirement_ids(tmp_path):
    """「1장의 요건」 칸에는 1장의 ID(OR-…)를 쓰고, 분류가 맞고, 운영요건.md에 있어야 한다(M5)."""
    files = {"docs/운영/운영요건지도.md": MAP, "docs/운영/운영요건.md": REQS, "security/scan_secrets.py": "",
             "tests/x.py": "", "CLAUDE.md": "", "requirements.lock": "", ".github/workflows/ci.yml": ""}
    repo = git_repo(tmp_path, files)
    install(repo, "ops/map/check_map.py", "ops/map/check_map.py")
    assert run(repo, "ops/map/check_map.py").returncode == 0
    broken = (MAP.replace("OR-SEC-02 비밀 정보", "비밀 정보")
                 .replace("OR-REL-08", "OR-CON-08")
                 .replace("OR-REP-02", "OR-REP-09"))
    (repo / "docs/운영/운영요건지도.md").write_text(broken, encoding="utf-8")
    result = run(repo, "ops/map/check_map.py")
    assert result.returncode == 1
    assert "1행(보안): 1장의 요건 ID(OR-…)가 없다" in result.stdout
    assert "OR-CON-08의 분류가 요건(신뢰성=REL)과 다르다" in result.stdout
    assert "OR-REP-09가 docs/운영/운영요건.md에 없다" in result.stdout


def test_check_code_rules(tmp_path):
    good = {
        "api/llm.py": "import anthropic\n",
        "api/main.py": "from api import llm\n",
        "web/js/list.js": "cell.textContent = job.title;\n",
        "prompts/summary_v1.txt": "### system\n### user\n",
        "prompts/ask_v1.txt": "### system\n### user\n",
        ".env.example": "PROMPT_SUMMARY=summary_v1\n",
    }
    repo = git_repo(tmp_path, good)
    install(repo, "기준산출물/ops/rules/check_code_rules.py", "ops/rules/check_code_rules.py")
    assert run(repo, "ops/rules/check_code_rules.py").returncode == 0

    (repo / "api/main.py").write_text('import anthropic\nMODEL = "claude-haiku-5-5"\n', encoding="utf-8")
    (repo / "web/js/list.js").write_text("cell.innerHTML = job.title;\n", encoding="utf-8")
    (repo / ".env.example").write_text("PROMPT_SUMMARY=summary_v9\n", encoding="utf-8")
    result = run(repo, "ops/rules/check_code_rules.py")
    assert result.returncode == 1
    for rule in ("llm-bypass", "inner-html", "model-name", "prompt-file"):
        assert rule in result.stdout


WORKFLOWS = ("ci/ci.yml", "ci/release.yml", "ci/pages.yml")


def test_kit_workflows_pass_check_pins(tmp_path):
    """키트의 워크플로 셋을 그대로 넣은 저장소에서 고정 검사가 통과한다(P1 액션 SHA, P3 python-version-file)."""
    files = {k: v for k, v in PINNED.items() if not k.startswith(".github/")}
    for name in WORKFLOWS:
        files[".github/workflows/" + Path(name).name] = (KIT / name).read_text(encoding="utf-8")
    repo = git_repo(tmp_path, files)
    install(repo, "ops/version/check_pins.py", "ops/version/check_pins.py")
    result = run(repo, "ops/version/check_pins.py")
    assert result.returncode == 0, result.stdout


def test_ci_job_names_are_the_required_checks():
    """보호 규칙의 필수 검사, ci_passed.sh, ruleset.json이 기다리는 이름이 ci.yml의 작업 이름과 같다."""
    text = (KIT / "ci/ci.yml").read_text(encoding="utf-8")
    for name in ("test", "eval", "secrets", "rules"):
        assert f"    name: {name}\n" in text
    assert 'REQUIRED_CHECKS:-test eval secrets rules' in (KIT / "ops/release/ci_passed.sh").read_text(encoding="utf-8")
    ruleset = (KIT / "ops/protect/ruleset.json").read_text(encoding="utf-8")
    for name in ("test", "eval", "secrets", "rules"):
        assert f'"context": "{name}"' in ruleset


def test_pages_reads_tag_only_through_environment():
    """사람이 넣는 태그(inputs.tag)를 run: 스크립트 안에 직접 끼워 넣지 않는다(스크립트 주입, 2-8)."""
    lines = (KIT / "ci/pages.yml").read_text(encoding="utf-8").splitlines()
    for line in lines:
        if line.strip().startswith("run:"):
            assert "${{" not in line, line
    assert "workflow_dispatch" in "\n".join(lines)
    assert "pages: write" in "\n".join(lines) and "id-token: write" in "\n".join(lines)
