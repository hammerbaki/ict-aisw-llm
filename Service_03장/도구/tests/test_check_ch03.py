"""check_ch03.py의 테스트. 임시 폴더에 작은 저장소를 만들어 점검 결과를 확인한다.

실행: 도구 폴더에서  python -m pytest -q
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_ch03  # noqa: E402

INTRO = "# 서비스 소개\n\n## 한 줄 소개\n\n- 한 줄 소개: (작성 전)\n\n## 끝\n"


def run(repo, *args, name="개발자A", email="a@example.com"):
    subprocess.run(
        ["git", "-c", f"user.name={name}", "-c", f"user.email={email}", "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def write(repo, text, filename="서비스소개.md"):
    (repo / filename).write_text(text, encoding="utf-8", newline="\n")


def make_repo(tmp_path):
    """두 사람이 같은 줄을 고쳐 충돌을 해결하고, 풀 리퀘스트 두 개가 병합된 저장소."""
    repo = tmp_path / "lab"
    repo.mkdir()
    run(repo, "init", "-q", "-b", "main")
    write(repo, INTRO)
    run(repo, "add", ".")
    run(repo, "commit", "-qm", "시작 파일", name="교수", email="prof@example.com")

    run(repo, "switch", "-qc", "1-a")
    write(repo, INTRO.replace("(작성 전)", "A의 문장"))
    run(repo, "commit", "-qam", "A의 한 줄 소개")

    run(repo, "switch", "-q", "main")
    run(repo, "switch", "-qc", "2-b")
    write(repo, INTRO.replace("(작성 전)", "B의 문장"))
    run(repo, "commit", "-qam", "B의 한 줄 소개", name="개발자B", email="b@example.com")

    run(repo, "switch", "-q", "main")
    run(repo, "merge", "-q", "--no-ff", "1-a", "-m", "Merge pull request #3 from team01/1-a")

    run(repo, "switch", "-q", "2-b")
    result = subprocess.run(["git", "-C", str(repo), "-c", "user.name=개발자B",
                             "-c", "user.email=b@example.com", "merge", "main"],
                            capture_output=True)
    assert result.returncode == 1          # 충돌이 나야 한다
    write(repo, INTRO.replace("(작성 전)", "A와 B를 합친 문장"))
    run(repo, "add", "서비스소개.md")
    run(repo, "commit", "-q", "--no-edit", name="개발자B", email="b@example.com")

    run(repo, "switch", "-q", "main")
    run(repo, "merge", "-q", "--no-ff", "2-b", "-m", "Merge pull request #4 from team01/2-b")
    return repo


def test_all_pass(tmp_path, capsys):
    repo = make_repo(tmp_path)
    assert check_ch03.main(["--lab", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "병합된 풀 리퀘스트: 2개 (#3, #4)" in out
    assert "충돌 해결 커밋: 1개" in out
    assert "개발자B" in out


def test_author_counts_only_own_pull_requests(tmp_path, capsys):
    repo = make_repo(tmp_path)
    assert check_ch03.main(["--lab", str(repo), "--author", "b@example"]) == 1
    assert "내가 작성한 풀 리퀘스트: 1개 (#4)" in capsys.readouterr().out


def test_marker_left_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, INTRO + "<<<<<<< HEAD\n가\n=======\n나\n>>>>>>> main\n")
    run(repo, "commit", "-qam", "충돌 표시를 남긴 채 커밋")
    assert check_ch03.main(["--lab", str(repo)]) == 1
    assert "[미통과] 충돌 표시" in capsys.readouterr().out


def test_squash_subject_is_counted(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "메모\n", filename="memo.md")
    run(repo, "add", "memo.md")
    run(repo, "commit", "-qm", "팀원 소개 파일 추가 (#7)")
    check_ch03.main(["--lab", str(repo)])
    assert "3개 (#3, #4, #7)" in capsys.readouterr().out


def test_no_conflict_resolution_fails(tmp_path, capsys):
    repo = tmp_path / "lab"
    repo.mkdir()
    run(repo, "init", "-q", "-b", "main")
    write(repo, INTRO)
    run(repo, "add", ".")
    run(repo, "commit", "-qm", "시작 파일")
    for n in (1, 2):
        run(repo, "switch", "-qc", f"{n}-x", "main")
        write(repo, f"{n}\n", filename=f"f{n}.md")
        run(repo, "add", ".")
        run(repo, "commit", "-qm", f"파일 {n}")
        run(repo, "switch", "-q", "main")
        run(repo, "merge", "-q", "--no-ff", f"{n}-x", "-m", f"Merge pull request #{n} from t/{n}-x")
    assert check_ch03.main(["--lab", str(repo)]) == 1
    assert "[미통과] 충돌 해결 커밋" in capsys.readouterr().out


def test_old_git_fallback(tmp_path, capsys, monkeypatch):
    """git 2.38 미만처럼 --write-tree가 없을 때도 충돌 해결 커밋을 찾는다."""
    repo = make_repo(tmp_path)
    real_git = check_ch03.git

    def old_git(lab, *args, check=True):
        if "--write-tree" in args:
            return subprocess.CompletedProcess(args, 129, "", "usage: git merge-tree")
        return real_git(lab, *args, check=check)

    monkeypatch.setattr(check_ch03, "git", old_git)
    assert check_ch03.main(["--lab", str(repo)]) == 0
    assert "충돌 해결 커밋: 1개" in capsys.readouterr().out


def test_record(tmp_path, capsys):
    repo = make_repo(tmp_path)
    record = tmp_path / "협업기록.md"
    template = Path(__file__).resolve().parents[2] / "협업기록_양식.md"
    record.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    assert check_ch03.main(["--lab", str(repo), "--record", str(record)]) == 1
    assert "[미통과] 협업기록" in capsys.readouterr().out

    record.write_text(
        "- https://github.com/class-org/team01-lab/pull/3\n"
        "- https://github.com/class-org/team01-lab/pull/4\n",
        encoding="utf-8",
    )
    assert check_ch03.main(["--lab", str(repo), "--record", str(record)]) == 0


def test_missing_repo_returns_2(tmp_path):
    assert check_ch03.main(["--lab", str(tmp_path / "없음")]) == 2
