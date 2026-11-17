"""커밋 메시지와 브랜치 이름이 저장소 규약(docs/운영/저장소규약.md)을 따르는지 검사한다.

규약의 바탕은 Conventional Commits 1.0.0이다(https://www.conventionalcommits.org/en/v1.0.0/).
첫 줄의 형식: <종류>[(범위)][!]: <설명>

쓰는 법 (저장소 폴더에서)
    python ops/rules/check_commits.py --range main..HEAD      범위 안의 커밋(병합 커밋 제외)
    python ops/rules/check_commits.py --file 커밋메시지.txt    '---' 줄로 나눈 메시지 묶음
    python ops/rules/check_commits.py --message "feat: ..."    메시지 하나
    python ops/rules/check_commits.py --hook .git/COMMIT_EDITMSG   commit-msg 훅에서 부를 때
    python ops/rules/check_commits.py --branch                 지금 브랜치의 이름
    python ops/rules/check_commits.py --branch agent/issue-07-t1   이름 하나
위반이 하나라도 있으면 종료 코드 1로 끝난다.
"""

import argparse
import re
import subprocess
import sys

# 저장소 규약 2절의 종류 목록. 규약을 고치면 이 목록도 함께 고친다.
TYPES = ("feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert")
# 3장의 종류에 뒤의 장이 쓰는 종류를 더하였다: 8장 loop(루프 실험), practice(연습),
# 10장 agent(에이전트 하나의 작업 브랜치, 예: agent/issue-07-t1). 10장의 통합 브랜치 feat/issue-07은 feat이다.
BRANCH_TYPES = ("feat", "fix", "docs", "test", "refactor", "chore", "ci", "agent", "loop", "practice")
MAX_HEADER = 72  # 첫 줄의 최대 글자 수

HEADER = re.compile(r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^()\s]+)\))?(?P<bang>!)?: (?P<desc>\S.*)$")
BRANCH = re.compile(r"^(?P<type>[a-z]+)/[a-z0-9]+(?:-[a-z0-9]+)*$")


def check_message(message):
    """메시지 하나를 검사해 위반 사유의 목록을 돌려준다. 빈 목록이면 통과이다."""
    lines = message.strip("\n").split("\n")
    header = lines[0] if lines else ""
    problems = []
    found = HEADER.match(header)
    if not found:
        problems.append("첫 줄이 '<종류>(범위): 설명' 형식이 아니다")
    else:
        if found["type"] != found["type"].lower():
            # 명세(1.0.0의 15항)는 대소문자를 가리지 않지만, 이 저장소의 규약은 소문자로 정하였다
            problems.append("종류는 소문자로 쓴다(저장소 규약)")
        elif found["type"] not in TYPES:
            problems.append(f"종류 '{found['type']}'는 규약에 없다(허용: {', '.join(TYPES)})")
        if found["desc"].endswith("."):
            problems.append("설명 끝에 마침표를 찍지 않는다")
    if len(header) > MAX_HEADER:
        problems.append(f"첫 줄이 {len(header)}자이다({MAX_HEADER}자 이하)")
    if len(lines) > 1 and lines[1].strip():
        problems.append("본문은 첫 줄 다음에 빈 줄을 하나 두고 쓴다")
    return problems


def check_branch(name):
    """브랜치 이름을 검사해 위반 사유의 목록을 돌려준다. main은 검사하지 않는다."""
    if name == "main":
        return []
    found = BRANCH.match(name)
    if not found:
        return ["브랜치 이름이 '<종류>/<영문-소문자-설명>' 형식이 아니다"]
    if found["type"] not in BRANCH_TYPES:
        return [f"브랜치 종류 '{found['type']}'는 규약에 없다(허용: {', '.join(BRANCH_TYPES)})"]
    return []


def strip_comments(text):
    """git이 편집기에 넣는 '#' 주석 줄을 뺀다(commit-msg 훅에서 읽은 파일)."""
    return "\n".join(line for line in text.split("\n") if not line.startswith("#"))


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout


def commits_in_range(repo, rev_range):
    """범위 안의 (짧은 해시, 메시지) 목록. 병합 커밋은 뺀다."""
    out = git(repo, "log", "--no-merges", "--reverse", "--format=%h%x1f%B%x1e", rev_range)
    commits = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if record:
            sha, _, body = record.partition("\x1f")
            commits.append((sha, body))
    return commits


def report(items):
    """(이름, 메시지) 목록을 검사해 결과를 찍고 위반 건수를 돌려준다."""
    bad = 0
    for name, message in items:
        problems = check_message(message)
        header = message.strip().split("\n")[0] if message.strip() else "(빈 메시지)"
        if problems:
            bad += 1
            print(f"위반 {name}: {header}")
            for problem in problems:
                print(f"    - {problem}")
        else:
            print(f"통과 {name}: {header}")
    print(f"검사 {len(items)}건, 위반 {bad}건")
    return bad


def main(argv=None):
    parser = argparse.ArgumentParser(description="커밋 메시지와 브랜치 이름 검사")
    parser.add_argument("--repo", default=".", help="저장소 폴더(기본: 지금 폴더)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--range", help="git 범위. 예: main..HEAD, tdd-1..HEAD")
    group.add_argument("--file", help="'---' 줄로 나눈 메시지 묶음 파일")
    group.add_argument("--message", help="메시지 하나")
    group.add_argument("--hook", help="commit-msg 훅이 넘기는 메시지 파일")
    group.add_argument("--branch", nargs="?", const="", help="브랜치 이름(값이 없으면 지금 브랜치)")
    args = parser.parse_args(argv)

    if args.branch is not None:
        name = args.branch or git(args.repo, "branch", "--show-current").strip()
        problems = check_branch(name)
        print(f"{'위반' if problems else '통과'} 브랜치: {name}")
        for problem in problems:
            print(f"    - {problem}")
        return 1 if problems else 0
    if args.range:
        items = commits_in_range(args.repo, args.range)
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            chunks = re.split(r"^---$", f.read(), flags=re.M)
        items = [(f"#{n}", chunk) for n, chunk in enumerate((c for c in chunks if c.strip()), 1)]
    elif args.hook:
        with open(args.hook, encoding="utf-8") as f:
            items = [("커밋", strip_comments(f.read()))]
    else:
        items = [("메시지", args.message)]
    return 1 if report(items) else 0


if __name__ == "__main__":
    sys.exit(main())
