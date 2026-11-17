"""(11장 키트의 사본: 3장 키트 ops/rules/globmatch.py를 그대로 옮겼다.)

경로 패턴(glob)을 정규식으로 바꾸어 맞추어 보는 작은 도구.

lint_rules.py(경로별 규칙의 paths가 실제 파일에 맞는지)와 perm_sim.py(Read·Edit 권한 규칙)가 함께 쓴다.
규칙은 gitignore 형식을 단순화한 것이다.

- `*`는 경로 한 마디(슬래시 사이) 안의 아무 글자, `**`는 여러 마디에 걸친 아무 글자이다.
- `?`는 한 글자이다. `{a,b}`는 a와 b 두 패턴으로 펼친다.
- 슬래시가 없는 패턴(예: `.env`, `*.md`)은 어느 깊이에서나 맞는다.
- 슬래시가 있는 패턴(예: `api/**`, `/docs/*.md`)은 기준 폴더에서부터 맞춘다.
"""

import re


def expand_braces(pattern):
    """`{a,b}`를 펼쳐 패턴 목록을 돌려준다. 중첩되지 않은 중괄호만 다룬다."""
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    head, tail = pattern[:match.start()], pattern[match.end():]
    result = []
    for choice in match.group(1).split(","):
        result.extend(expand_braces(head + choice + tail))
    return result


def to_regex(pattern):
    """패턴 하나를 정규식 문자열로 바꾼다. 앞의 `./`와 `/`는 기준 폴더를 뜻하므로 떼어 낸다."""
    anchored = "/" in pattern.rstrip("/")
    if pattern.startswith("./"):
        pattern = pattern[2:]
    pattern = pattern.lstrip("/")
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    body = "".join(out)
    if not anchored:
        body = "(?:.*/)?" + body  # 슬래시 없는 패턴은 어느 깊이에서나 맞는다
    return "^" + body + "$"


def matches(pattern, path):
    """path(기준 폴더에서의 상대 경로, 슬래시 구분)가 pattern에 맞는가."""
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    return any(re.match(to_regex(p), path) for p in expand_braces(pattern))
