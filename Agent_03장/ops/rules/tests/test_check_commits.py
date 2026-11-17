"""check_commits.py의 테스트: 커밋 메시지와 브랜치 이름의 규약 검사."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_commits import check_branch, check_message, commits_in_range, strip_comments  # noqa: E402


@pytest.mark.parametrize("message", [
    "feat(api): 공고 목록에 마감 임박 필터 추가",
    "fix: 빈 질문을 422로 거절",
    "docs: 저장소 규약 추가",
    "feat(web)!: 응답의 키 이름 변경\n\n화면 코드도 함께 고쳐야 한다.",
    "test(api): 경계값 테스트 추가\n\nRefs: REQ-SUM-05",
    "test(REQ-JOB-06): 마감 임박 필터의 테스트와 동결 기록 (Red)",  # 2장: 범위에 요구 ID
    "build: requirements.lock 추가",
    "ci: 테스트 작업 추가",
    "revert: 마감 임박 필터 추가를 되돌림",
])
def test_valid_messages_pass(message):
    assert check_message(message) == []


@pytest.mark.parametrize("message, reason", [
    ("요약 응답에 걸린 시간 추가", "형식"),
    ("update: 설정 파일 수정", "규약에 없다"),
    ("Feat: 마감 임박 배너", "소문자"),
    ("docs: CLAUDE.md에 실행 명령 추가.", "마침표"),
    ("feat: 첫 줄\n본문을 빈 줄 없이 이었다", "빈 줄"),
    ("feat:콜론 뒤에 빈칸이 없다", "형식"),
    ("chore: " + "가" * 70, "72자"),
])
def test_invalid_messages_are_reported(message, reason):
    problems = check_message(message)
    assert problems
    assert any(reason in p for p in problems)


@pytest.mark.parametrize("name, ok", [
    ("main", True),
    ("chore/team-rules", True),
    ("feat/closing-within", True),
    ("feat/issue-07", True),          # 10장의 통합 브랜치
    ("agent/issue-07-t1", True),      # 10장의 에이전트 작업 브랜치
    ("loop/success-1", True),         # 8장의 루프 실험
    ("practice/bug", True),           # 8장의 연습
    ("agent/Issue_07", False),
    ("loops/success-1", False),
    ("feature/team-rules", False),
    ("chore/Team_Rules", False),
    ("team-rules", False),
    ("docs/규약", False),
])
def test_branch_names(name, ok):
    assert (check_branch(name) == []) is ok


def test_strip_comments_removes_git_editor_lines():
    text = "fix: 오류 고침\n\n# Please enter the commit message\n# On branch main\n"
    assert check_message(strip_comments(text)) == []


def run(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_commits_in_range_skips_merges(tmp_path):
    run(tmp_path, "init", "-q", "-b", "main")
    run(tmp_path, "config", "user.name", "t")
    run(tmp_path, "config", "user.email", "t@example.com")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    run(tmp_path, "add", "a.txt")
    run(tmp_path, "commit", "-q", "-m", "chore: 시작")
    run(tmp_path, "tag", "base")
    run(tmp_path, "switch", "-q", "-c", "feat/b")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    run(tmp_path, "add", "b.txt")
    run(tmp_path, "commit", "-q", "-m", "b 추가")
    run(tmp_path, "switch", "-q", "main")
    run(tmp_path, "merge", "-q", "--no-ff", "-m", "Merge branch 'feat/b'", "feat/b")
    commits = commits_in_range(str(tmp_path), "base..HEAD")
    assert [msg.strip() for _, msg in commits] == ["b 추가"]
