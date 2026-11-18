"""키 노출 검사기는 심어 둔 가짜 키를 찾아내고, 깨끗한 폴더는 통과시키는가."""
import shutil
import subprocess

import pytest

from tools.check_secrets import check

FAKE_KEY = "sk-ant-" + "test" + "x" * 24  # 실제 키가 아닌 시험용 문자열(실행 중에 만든다)
NAME = "ANTHROPIC_" + "API_KEY"  # 이 테스트 파일 자체가 검사에 걸리지 않도록 이름도 실행 중에 만든다


def make_repo(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "summary.js").write_text("fetch('/api/summary')\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".env\n.venv/\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text(NAME + "=\nLLM_FAKE=1\n", encoding="utf-8")
    return tmp_path


def test_clean(tmp_path):
    assert check(make_repo(tmp_path)) == []


def test_key_in_browser_code(tmp_path):
    root = make_repo(tmp_path)
    (root / "web" / "summary.js").write_text(
        f"fetch('https://api.anthropic.com/v1/messages', {{headers: {{'x-api-key': '{FAKE_KEY}'}}}})\n",
        encoding="utf-8")
    problems = check(root)
    assert any("키 모양" in p for p in problems)
    assert any("직접 부름" in p for p in problems)
    assert all(FAKE_KEY not in p for p in problems)  # 찾은 값은 가려서 보인다


def test_value_in_env_example(tmp_path):
    root = make_repo(tmp_path)
    (root / ".env.example").write_text(NAME + "=abc123secret\n", encoding="utf-8")
    assert any("값이 적혀" in p for p in check(root))


def test_dotenv_itself_is_allowed(tmp_path):
    root = make_repo(tmp_path)
    (root / ".env").write_text(f"{NAME}={FAKE_KEY}\n", encoding="utf-8")
    assert check(root) == []  # git 저장소가 아니면 .env 파일 자체는 문제 삼지 않는다


@pytest.mark.skipif(shutil.which("git") is None, reason="git 없음")
def test_tracked_dotenv(tmp_path):
    root = make_repo(tmp_path)
    (root / ".env").write_text("LLM_FAKE=1\n", encoding="utf-8")
    run = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, check=True)  # noqa: E731
    run("init", "-q")
    run("add", "-f", ".env")
    assert any(".env 가 git에" in p for p in check(root))


@pytest.mark.skipif(shutil.which("git") is None, reason="git 없음")
def test_dotenv_not_ignored(tmp_path):
    root = make_repo(tmp_path)
    (root / ".gitignore").write_text(".venv/\n", encoding="utf-8")  # .env 줄이 빠졌다
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    assert any("제외되지 않음" in p for p in check(root))


@pytest.mark.skipif(shutil.which("git") is None, reason="git 없음")
def test_parent_gitignore_counts(tmp_path):
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")  # 저장소 맨 위의 .gitignore
    sub = tmp_path / "ch09"
    sub.mkdir()
    make_repo(sub)
    (sub / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert check(sub) == []
