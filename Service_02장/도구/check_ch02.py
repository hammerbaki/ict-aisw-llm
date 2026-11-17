"""2장 완료 기준 점검기.

개인 실습 저장소가 2장의 완료 기준을 충족하는지 저장소의 상태만 보고 판정한다.
Claude Code의 대화 내용은 보지 않는다. 판정은 커밋, 파일, 프로그램과 테스트의 실행 결과로 한다.

사용법 (가상 환경을 켠 터미널에서):
    python ~/kits/Service_02장/도구/check_ch02.py ~/llm-service-lab

선택 과제(12-10, 정렬 옵션)는 [선택 · …]으로 따로 보이고 통과 수에 넣지 않는다.
"""
import os
import subprocess
import sys
from pathlib import Path

results = []
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}


def check(name, ok, hint=""):
    results.append(ok)
    mark = "통과" if ok else "미통과"
    line = f"[{mark}] {name}"
    if not ok and hint:
        line += f"\n         → {hint}"
    print(line)


def optional(name, ok, hint=""):
    mark = "선택 · 통과" if ok else "선택 · 미통과"
    line = f"[{mark}] {name}"
    if not ok and hint:
        line += f"\n         → {hint}"
    print(line)


def git(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout.strip()


def run_program(folder, *args):
    proc = subprocess.run([sys.executable, "deadline.py", "--today", "2027-03-15", *args],
                          cwd=folder, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV)
    return proc.returncode, proc.stdout.strip().splitlines()


def run_tests(folder):
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=folder, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV)
    out = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode, (out[-1].strip() if out else "")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    repo = Path(sys.argv[1]).expanduser().resolve()

    code, top = git(repo, "rev-parse", "--show-toplevel")
    check("저장소이다", code == 0, "git init을 했는지, 경로가 맞는지 확인한다")
    if code != 0:
        print(f"\n{sum(results)}/{len(results)} 통과")
        sys.exit(1)

    code, branch = git(repo, "branch", "--show-current")
    check("현재 브랜치가 main이다", branch == "main",
          f"지금 브랜치는 '{branch}'이다. git switch main")

    _, name = git(repo, "config", "user.name")
    _, email = git(repo, "config", "user.email")
    check("커밋 작성자(user.name, user.email)가 설정되어 있다", bool(name and email),
          "git config --global user.name / user.email (부록 A-9)")

    _, tracked = git(repo, "ls-files")
    tracked = tracked.splitlines()
    check(".gitignore가 커밋되어 있다", ".gitignore" in tracked,
          "견본을 .gitignore로 복사하고 커밋한다(3-4)")
    check(".venv/가 커밋되지 않았다", not any(p.startswith(".venv/") for p in tracked),
          "git rm -r --cached .venv 후 .gitignore에 .venv/를 넣고 커밋한다")
    secret = [p for p in tracked if Path(p).name == ".env" or Path(p).name.startswith(".env.")
              and not p.endswith(".env.example")]
    check(".env 같은 비밀 정보 파일이 커밋되지 않았다", not secret,
          f"커밋된 파일: {secret}. 되돌리기 상황표의 「비밀 정보를 커밋했다」를 본다")
    check("CLAUDE.md가 커밋되어 있다", "CLAUDE.md" in tracked, "/init으로 만들고 고친 뒤 커밋한다(12-2)")
    check("ch01/이 커밋되어 있다", any(p.startswith("ch01/") for p in tracked),
          "3-4의 첫 커밋을 확인한다")
    for f in ["ch02/deadline/deadline.py", "ch02/deadline/dday.py", "ch02/deadline/README.md"]:
        check(f"{f}가 커밋되어 있다", f in tracked)

    _, count = git(repo, "rev-list", "--count", "main")
    count = int(count or 0)
    check(f"main의 커밋이 8개 이상이다 (지금 {count}개)", count >= 8,
          "따라 하기에서 2개(1장 결과물, 골격), 핵심 실습에서 CLAUDE.md 1개·변경 3개·되돌리기 1개·작업기록 1개")

    _, subjects = git(repo, "log", "main", "--format=%s")
    subjects = subjects.splitlines()
    check("git revert로 만든 커밋이 있다", any(s.startswith('Revert "') for s in subjects),
          "git revert <커밋> 으로 되돌린다. 손으로 고쳐 커밋한 것은 해당하지 않는다")

    code, test_src = git(repo, "show", "main:ch02/deadline/tests/test_deadline.py")
    check("CSV 순서를 지키는 테스트 test_render_keeps_csv_order가 main에 있다",
          code == 0 and "def test_render_keeps_csv_order" in test_src,
          "정렬 커밋을 git revert로 되돌렸는지, 기존 테스트를 고친 커밋이 남았는지 본다")

    _, remotes = git(repo, "remote")
    check("원격 origin이 등록되어 있다", "origin" in remotes.split(),
          "git remote add origin <주소> (11-4)")
    code, upstream = git(repo, "rev-parse", "--abbrev-ref", "main@{upstream}")
    check("main이 원격 브랜치를 추적한다", code == 0,
          "git push -u origin main")
    if code == 0:
        _, ahead = git(repo, "rev-list", "--count", f"{upstream}..main")
        check("푸시하지 않은 커밋이 없다", ahead == "0",
              f"{ahead}개 커밋이 원격에 없다. git push")

    folder = repo / "ch02" / "deadline"
    if (folder / "deadline.py").exists():
        _, lines = run_program(folder)
        check("기본 출력이 CSV 순서를 따른다 (첫 줄이 한빛데이터)",
              bool(lines) and "한빛데이터" in lines[0])
        text = "\n".join(lines)
        check("마감 당일은 D-DAY, 지난 공고는 마감으로 표시한다",
              "D-DAY" in text and "마감" in text)
        code, last = run_tests(folder)
        check(f"테스트가 모두 통과한다 ({last})", code == 0,
              "No module named pytest이면 가상 환경을 켠 터미널에서 점검기를 실행한다(부록 A-13-1)")
        code, sorted_lines = run_program(folder, "--sort", "deadline")
        if code == 2:
            print("[선택 · 하지 않음] --sort deadline 옵션 (12-10)")
        else:
            optional("--sort deadline이면 마감일 순이다 (첫 줄이 가람소프트)",
                     bool(sorted_lines) and "가람소프트" in sorted_lines[0],
                     "옵션의 이름과 값이 지시 B와 같은지 본다")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} 통과")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
