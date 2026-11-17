"""3장 완료 기준 점검.

팀 실습 저장소의 로컬 클론과 개인 저장소의 협업기록을 읽어, 3장의 완료 기준을 점검한다.
GitHub에 접속하지 않는다. 점검 전에 팀 실습 저장소에서 `git fetch`를 한 번 실행해 둔다.

사용법
    python check_ch03.py --lab ~/teams/team01-lab
    python check_ch03.py --lab ~/teams/team01-lab --author 「GitHub 아이디 또는 커밋 이메일」
    python check_ch03.py --lab ~/teams/team01-lab --author hong --record ~/llm-service-lab/ch03/협업기록.md

점검 항목
    1. 충돌 표시: 기준 브랜치(기본 origin/main)의 파일에 <<<<<<< 나 >>>>>>> 로 시작하는 줄이 없다
    2. 병합된 풀 리퀘스트: 「Merge pull request #n」 또는 「제목 (#n)」 커밋이 2개 이상
    3. 내가 작성한 풀 리퀘스트: --author를 주면, 그 사람이 커밋한 풀 리퀘스트가 2개 이상
    4. 충돌 해결 커밋: 풀 리퀘스트 병합이 아닌 병합 커밋 가운데 실제로 충돌이 있던 것이 1개 이상
    5. 협업기록: --record를 주면, 「(작성)」이 남지 않고 풀 리퀘스트 주소가 2개 이상

끝 코드: 모두 통과하면 0, 하나라도 통과하지 못하면 1, 저장소를 읽지 못하면 2
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

PR_MERGE = re.compile(r"^Merge pull request #(\d+)")
SQUASH = re.compile(r"\(#(\d+)\)\s*$")
PR_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+")
MARKER = r"^(<<<<<<<|>>>>>>>)( |$)"
PLACEHOLDER = "(작성)"


def git(lab, *args, check=True):
    result = subprocess.run(
        ["git", "-C", str(lab), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} 실패")
    return result


def pick_ref(lab, ref):
    if ref:
        return ref
    has_remote = git(lab, "rev-parse", "--verify", "--quiet", "origin/main", check=False)
    return "origin/main" if has_remote.returncode == 0 else "HEAD"


def commits(lab, ref):
    """(해시, 부모 목록, 작성자 이름, 작성자 이메일, 제목)의 목록."""
    out = git(lab, "log", "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%s", ref).stdout
    rows = []
    for line in out.splitlines():
        sha, parents, name, email, subject = line.split("\x1f", 4)
        rows.append((sha, parents.split(), name, email, subject))
    return rows


def pr_number(parents, subject):
    m = PR_MERGE.match(subject)
    if m and len(parents) >= 2:
        return int(m.group(1))
    m = SQUASH.search(subject)
    if m and len(parents) == 1:
        return int(m.group(1))
    return None


def pr_authors(lab, sha, parents, name, email):
    """풀 리퀘스트에 들어간 커밋의 작성자(이름, 이메일) 집합."""
    if len(parents) == 1:          # 스쿼시 병합: 커밋 하나의 작성자
        return {(name, email)}
    out = git(lab, "log", "--no-merges", "--format=%an%x1f%ae", f"{parents[0]}..{parents[1]}").stdout
    return {tuple(line.split("\x1f", 1)) for line in out.splitlines() if line}


def had_conflict(lab, parents):
    """두 부모를 다시 합쳐 보아 충돌이 있었는지 판정한다.

    git 2.38 이상은 `merge-tree --write-tree`를 쓰고, 그보다 낮으면 예전 형식의
    `merge-tree <공통 조상> <부모1> <부모2>` 출력에서 충돌 표시를 찾는다.
    돌려주는 값: True(충돌 있음), False(충돌 없음), None(판정할 수 없음)
    """
    result = git(lab, "merge-tree", "--write-tree", parents[0], parents[1], check=False)
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    base = git(lab, "merge-base", parents[0], parents[1], check=False)
    if base.returncode != 0:
        return None
    legacy = git(lab, "merge-tree", base.stdout.strip(), parents[0], parents[1], check=False)
    if legacy.returncode != 0:
        return None
    return "<<<<<<<" in legacy.stdout


def matches(author, people):
    key = author.lower()
    return any(key in name.lower() or key in email.lower() for name, email in people)


def check_lab(lab, ref, author):
    results = []
    marker = git(lab, "grep", "-n", "-E", MARKER, ref, "--", check=False)
    if marker.returncode == 1:
        results.append((True, "충돌 표시", "기준 브랜치의 파일에 충돌 표시가 없다"))
    else:
        lines = marker.stdout.strip().splitlines()[:5]
        results.append((False, "충돌 표시", "남아 있다: " + "; ".join(lines)))

    rows = commits(lab, ref)
    prs, mine, resolved, unknown = [], [], [], []
    for sha, parents, name, email, subject in rows:
        number = pr_number(parents, subject)
        if number is not None:
            prs.append(number)
            if author and matches(author, pr_authors(lab, sha, parents, name, email)):
                mine.append(number)
            continue
        if len(parents) >= 2:
            state = had_conflict(lab, parents)
            label = f"{sha[:7]} {subject}"
            if state is True:
                resolved.append((label, name, email))
            elif state is None:
                unknown.append(label)

    prs_text = ", ".join(f"#{n}" for n in sorted(prs)) or "없음"
    results.append((len(prs) >= 2, "병합된 풀 리퀘스트", f"{len(prs)}개 ({prs_text})"))
    if author:
        mine_text = ", ".join(f"#{n}" for n in sorted(mine)) or "없음"
        results.append((len(mine) >= 2, "내가 작성한 풀 리퀘스트", f"{len(mine)}개 ({mine_text})"))
    if resolved:
        text = "; ".join(f"{label} [{name}]" for label, name, _ in resolved)
        results.append((True, "충돌 해결 커밋", f"{len(resolved)}개: {text}"))
    elif unknown:
        results.append((False, "충돌 해결 커밋",
                        "판정하지 못하였다(git 2.38 이상 필요). 후보: " + "; ".join(unknown)))
    else:
        results.append((False, "충돌 해결 커밋", "없다. 충돌을 해결한 브랜치가 merge commit 방식으로 병합되었는지 확인한다"))
    return results


def check_record(path):
    p = Path(path).expanduser()
    if not p.exists():
        return [(False, "협업기록", f"파일이 없다: {p}")]
    text = p.read_text(encoding="utf-8")
    left = text.count(PLACEHOLDER)
    urls = set(PR_URL.findall(text))
    ok = left == 0 and len(urls) >= 2
    return [(ok, "협업기록", f"「{PLACEHOLDER}」 {left}곳 남음, 풀 리퀘스트 주소 {len(urls)}개")]


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="3장 완료 기준 점검")
    parser.add_argument("--lab", required=True, help="팀 실습 저장소의 로컬 클론 경로")
    parser.add_argument("--ref", help="점검할 브랜치(기본: origin/main, 없으면 HEAD)")
    parser.add_argument("--author", help="내 GitHub 아이디, 이름 또는 커밋 이메일의 일부")
    parser.add_argument("--record", help="ch03/협업기록.md 경로")
    args = parser.parse_args(argv)

    lab = Path(args.lab).expanduser()
    try:
        ref = pick_ref(lab, args.ref)
        results = check_lab(lab, ref, args.author)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"[오류] 저장소를 읽지 못하였다: {exc}")
        return 2
    if args.record:
        results += check_record(args.record)

    print(f"점검한 브랜치: {ref}")
    for ok, name, detail in results:
        print(f"[{'통과' if ok else '미통과'}] {name}: {detail}")
    passed = sum(1 for ok, _, _ in results if ok)
    print(f"결과: {passed}/{len(results)} 통과")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
