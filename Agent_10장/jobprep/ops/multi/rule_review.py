"""rule_review: 팀 규칙 가운데 기계로 잴 수 있는 것만 보는 규칙 검토기.

judge.sh의 기본 검토 명령이다. LLM 검토 에이전트(.claude/agents/reviewer.md)가 읽고 판단하는
일 가운데, 문자열로 확실히 가릴 수 있는 위반만 먼저 걸러 낸다. 사람이나 LLM 검토를 대신하지 않는다.

사용법 (작업 공간 안에서. judge.sh가 환경 변수를 넣어 부른다)
    MULTI_BASE=feat/issue-07 MULTI_BRANCH=agent/issue-07-t1 python ops/multi/rule_review.py

보는 규칙 (근거는 CLAUDE.md와 .claude/rules/. 괄호 끝은 검토 에이전트 reviewer.md의 검토 규칙 ID)
    W1  웹 코드에서 innerHTML, outerHTML, insertAdjacentHTML, document.write를 쓰지 않는다 (글은 textContent로만, RV3)
    W2  api/llm.py 밖에서 anthropic을 불러오지 않는다 (모든 LLM 호출은 api/llm.py, RV2)
    W3  키처럼 보이는 문자열(sk-ant-)이나 키 대입(ANTHROPIC_API_KEY=)을 코드와 문서에 넣지 않는다 (RV1)
    W4  기록(logging)에 요청 본문을 통째로 남기지 않는다 (body, text, question을 기록 인자로 넘기지 않는다, RV7)
W는 이 검토기의 번호이고, 1장 역할 정의서의 역할 ID(R1~R6)나 검토 규칙 ID(RV1~RV8)와 다르다.
출력: 첫 줄 「판정: 통과」 또는 「판정: 거부」, 그 아래 문제마다 「파일:줄 — 문제 — 근거」.
종료 코드: 통과 0, 거부 1, 실행 오류 2.
"""

import os
import re
import subprocess
import sys

RULES = [
    ("W1", re.compile(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML|document\.write"),
     lambda path: path.startswith("web/") and path.endswith((".js", ".html")),
     "HTML로 해석되는 삽입", "CLAUDE.md: 글은 textContent로만 넣는다"),
    ("W2", re.compile(r"^\s*(import anthropic|from anthropic\b)"),
     lambda path: path.endswith(".py") and path != "api/llm.py" and not path.startswith("tests/"),
     "api/llm.py 밖의 anthropic 불러오기", "CLAUDE.md: 모든 LLM 호출은 api/llm.py의 complete()"),
    ("W3", re.compile(r"sk-ant-|ANTHROPIC_API_KEY\s*=\s*\S"),
     lambda path: not path.endswith(".env.example"),
     "키처럼 보이는 값", "CLAUDE.md: 비밀 정보는 .env에만"),
    ("W4", re.compile(r"log\w*\.(info|warning|error|debug)\(.*\b(body|text|question)\b\s*[,)]"),
     lambda path: path.startswith("api/") and path.endswith(".py"),
     "기록에 요청 본문을 남김", "logs/README.md: 글자 수나 개수만 남긴다"),
]
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def added_lines(base, branch):
    """git diff base...branch 에서 더해진 줄을 (경로, 줄 번호, 내용)으로 돌려준다."""
    diff = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "-U0", f"{base}...{branch}"],
        capture_output=True, text=True, encoding="utf-8", check=True).stdout
    path, line_no = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            path = None if target == "/dev/null" else target[2:]
        elif line.startswith("@@"):
            match = HUNK.match(line)
            line_no = int(match.group(1)) if match else 0
        elif line.startswith("+") and path:
            yield path, line_no, line[1:]
            line_no += 1


def review(base, branch):
    problems = []
    for path, line_no, text in added_lines(base, branch):
        for code, pattern, applies, what, why in RULES:
            if applies(path) and pattern.search(text):
                problems.append(f"{path}:{line_no} — {code} {what} — {why}")
    return problems


def main():
    base = os.environ.get("MULTI_BASE")
    branch = os.environ.get("MULTI_BRANCH")
    if not base or not branch:
        print("판정: 거부\n실행 오류: MULTI_BASE와 MULTI_BRANCH를 정해야 한다")
        return 2
    try:
        problems = review(base, branch)
    except subprocess.CalledProcessError as error:
        print(f"판정: 거부\n실행 오류: {error.stderr.strip()}")
        return 2
    if problems:
        print("판정: 거부")
        print("\n".join(problems))
        return 1
    print("판정: 통과")
    print("문제 없음 (규칙 W1~W4)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
