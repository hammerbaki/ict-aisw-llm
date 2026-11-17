"""디자인토큰.md를 읽는 공용 모듈 (표준 라이브러리만 쓴다).

디자인토큰.md의 약속
- 토큰은 마크다운 표의 한 줄이다. 첫 칸은 토큰 이름, 둘째 칸은 값이며 둘 다 백틱으로 감싼다.
      | `gray-90` | `#111827` | 본문 글자의 기본 색 |
- 토큰 이름은 소문자, 숫자, 하이픈만 쓴다. CSS로 바꿀 때 앞에 `--`가 붙는다.
- 값에는 다른 토큰을 `{gray-90}`처럼 중괄호로 가리킬 수 있다(W3C 디자인 토큰 형식의 별칭 문법).
- 제목에 「대비 쌍」이 든 절의 표는 토큰이 아니라 대비를 잴 색의 쌍이다.
      | `color-text` | `color-bg` | 4.5 | 본문 글자 |
"""
import re
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9-]*$")
ALIAS = re.compile(r"\{([a-z][a-z0-9-]*)\}")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class TokenError(ValueError):
    """디자인토큰.md의 내용이 약속에 맞지 않을 때 낸다."""


def _cells(line):
    """표의 한 줄을 칸 목록으로 나눈다. 표가 아니면 None."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    cells = [c.strip() for c in s.strip("|").split("|")]
    if all(set(c) <= set("-: ") for c in cells):  # 구분 줄 |---|---|
        return None
    return cells


def _unquote(cell):
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`"):
        return cell[1:-1].strip()
    return None


def parse(text):
    """디자인토큰.md의 본문을 읽어 (tokens, pairs)를 돌려준다.

    tokens: 이름 -> {"value": 값, "group": 절 제목, "line": 줄 번호, "note": 설명}
    pairs:  [{"fg": 이름, "bg": 이름, "min": 기준, "use": 용도, "line": 줄 번호}]
    """
    tokens, pairs = {}, []
    heading = ""
    for no, line in enumerate(text.splitlines(), start=1):
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            continue
        cells = _cells(line)
        if not cells or len(cells) < 2:
            continue
        first, second = _unquote(cells[0]), _unquote(cells[1])
        if first is None or second is None:
            continue  # 머리 줄이거나 토큰이 아닌 표
        if "대비 쌍" in heading:
            if len(cells) < 3:
                raise TokenError(f"{no}줄: 대비 쌍에는 기준 칸이 있어야 한다")
            try:
                minimum = float(cells[2])
            except ValueError as exc:
                raise TokenError(f"{no}줄: 기준 {cells[2]!r}는 숫자가 아니다") from exc
            use = cells[3] if len(cells) > 3 else ""
            pairs.append({"fg": first, "bg": second, "min": minimum, "use": use, "line": no})
            continue
        if not NAME.match(first):
            raise TokenError(f"{no}줄: 토큰 이름 {first!r}는 소문자·숫자·하이픈만 쓴다")
        if first in tokens:
            raise TokenError(f"{no}줄: 토큰 {first!r}가 {tokens[first]['line']}줄에도 있다")
        note = cells[2] if len(cells) > 2 else ""
        tokens[first] = {"value": second, "group": heading, "line": no, "note": note}
    return tokens, pairs


def load(path):
    return parse(Path(path).read_text(encoding="utf-8"))


def resolve(name, tokens, _seen=None):
    """별칭을 끝까지 따라가 실제 값을 돌려준다. 순환 참조와 없는 토큰은 오류다."""
    seen = _seen or []
    if name in seen:
        raise TokenError("순환 참조: " + " -> ".join(seen + [name]))
    if name not in tokens:
        raise TokenError(f"없는 토큰 {name!r}를 가리킨다")
    value = tokens[name]["value"]
    whole = ALIAS.fullmatch(value)
    if whole:
        return resolve(whole.group(1), tokens, seen + [name])
    return value


def to_css_value(value):
    """`{gray-90}`을 `var(--gray-90)`로 바꾼다. 값 안에 섞인 별칭도 바꾼다."""
    return ALIAS.sub(lambda m: f"var(--{m.group(1)})", value)
