"""(11장 키트의 사본: 3장 키트 ops/rules/perm_sim.py를 그대로 옮겼다. naive_agent.py의 rules 층이 쓴다.)

권한 규칙의 판정을 흉내 내는 학습용 모의기이다. Claude Code가 실제로 쓰는 판정기가 아니다.

Claude Code 문서 「Configure permissions」(https://code.claude.com/docs/en/permissions, 2026-11-14 확인)의
규칙 가운데 다음만 옮겼다. 설정 파일을 읽고 "이 호출은 어떻게 판정될까"를 미리 따져 보는 데 쓴다.

1. 여러 설정 파일의 allow, ask, deny 목록을 합친다(목록은 덮어쓰지 않고 합쳐진다).
2. deny → ask → allow 순서로 보고 처음 맞는 것이 결과이다. 규칙이 얼마나 구체적인지는 따지지 않는다.
3. Bash: `*`는 공백을 포함한 아무 글자이다. 끝의 ` *`가 유일한 별표이면 맨 명령도 맞는다. `:*`는 ` *`와 같다.
   복합 명령(&&, ||, ;, |)은 나누어 보아, 하나라도 deny면 deny, ask면 ask, 모두 허용되어야 allow이다.
   cat, head, tail이 이름으로 읽는 파일에는 Read 거부 규칙도 적용한다.
4. Read, Edit: gitignore 형식의 경로 패턴. Read 거부는 같은 경로의 Edit도 막는다. Write는 Edit 규칙으로 본다.
   한 파일의 deny 목록 안에서 `!패턴`은 앞에 나온 규칙에서 그 경로를 빼낸다.
5. 맞는 규칙이 없으면 기본 동작(Manual 모드 기준)이다: 읽기 도구와 읽기 전용 명령은 허용, 나머지는 확인.
6. 보호 경로(.git, .claude 등)의 편집은 allow 규칙이 있어도 확인한다.

다루지 않는 것: 권한 모드별 차이, 훅, 샌드박스, 래퍼(timeout, nohup 등) 벗기기, 작업 폴더 밖 경로의
세부 규칙, MCP 도구, 매개변수 규칙, 작업 공간 신뢰, Windows의 PowerShell 도구와 그 규칙(Bash 거부 규칙이 있으면
PowerShell 도구가 꺼지는 것 포함), Windows 경로의 POSIX 정규화(C:\\Users\\… → /c/Users/…, 2026-11-17 문서 확인).
실제 판정은 Claude Code 안의 /permissions와 실행으로 확인한다.

쓰는 법 (저장소 폴더에서)
    python ops/rules/perm_sim.py "Bash(git push origin main)" "Read(.env)" --settings .claude/settings.json
    python ops/rules/perm_sim.py --cases 판정사례.txt --settings ~/.claude/settings.json .claude/settings.json
--settings는 파일을 여럿 받아 뒤의 인자를 모두 설정 파일로 읽는다. 그래서 판정할 호출을 먼저 적고
--settings를 맨 뒤에 둔다(--settings 바로 뒤에 호출을 이어 적으면 호출을 파일 이름으로 읽어 멈춘다).
판정 사례 파일은 한 줄에 `호출 => 기대`(deny, ask, allow)를 쓴다. 기대와 다르면 종료 코드 1이다.
"""

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from globmatch import matches  # noqa: E402

READ_ONLY = {"ls", "cat", "echo", "pwd", "head", "tail", "grep", "find", "wc", "which", "diff", "stat", "du", "cd"}
READ_ONLY_GIT = {"status", "log", "diff", "show"}
FILE_READERS = {"cat", "head", "tail"}
PROTECTED_DIRS = (".git/", ".claude/", ".vscode/", ".idea/", ".husky/", ".devcontainer/")
PROTECTED_FILES = {".gitconfig", ".gitmodules", ".bashrc", ".zshrc", ".profile", ".envrc", ".npmrc", ".mcp.json"}
CALL = re.compile(r"^(?P<tool>[A-Za-z_*][\w*]*)(?:\((?P<arg>.*)\))?$", re.S)


def load_settings(paths):
    """설정 파일마다 (이름, {"allow": [...], "ask": [...], "deny": [...]})를 돌려준다."""
    sources = []
    for path in paths:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        perms = data.get("permissions", {})
        label = str(path).replace("\\", "/")
        home = str(Path.home()).replace("\\", "/")
        if label.startswith(home + "/"):
            label = "~" + label[len(home):]  # 출력에서 홈 폴더를 ~로 줄인다
        sources.append((label, {kind: list(perms.get(kind, [])) for kind in ("allow", "ask", "deny")}))
    return sources


def parse_call(text):
    found = CALL.match(text.strip())
    if not found:
        raise ValueError(f"호출 형식이 아니다: {text}")
    return found["tool"], found["arg"]


def bash_matches(spec, command):
    """Bash 규칙의 지정자(spec)가 명령 하나에 맞는가."""
    spec = spec.strip()
    if spec.endswith(":*"):
        spec = spec[:-2] + " *"
    regex = "^" + ".*".join(re.escape(part) for part in spec.split("*")) + "$"
    if re.match(regex, command, re.S):
        return True
    return spec.endswith(" *") and spec.count("*") == 1 and command == spec[:-2]


def split_compound(command):
    """따옴표 밖의 &&, ||, ;, |, 줄바꿈으로 명령을 나눈다."""
    parts, buf, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        two = command[i:i + 2]
        if two in ("&&", "||"):
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch in ";|\n":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def path_matches(spec, path, kind):
    """Read, Edit 규칙의 경로 패턴이 path에 맞는가. deny와 ask에서는 `이름/**`가 어느 깊이에서나 맞는다."""
    if kind != "allow" and re.fullmatch(r"[^/*.][^/*]*/\*\*", spec):
        spec = "**/" + spec
    return matches(spec, path)


def path_rule(sources, kind, tools, path):
    """kind 목록에서 path에 맞는 (규칙, 파일)을 찾는다. 같은 파일 안의 `!패턴`은 앞의 규칙에서 빼낸다."""
    for name, perms in sources:
        hit = None
        for rule in perms[kind]:
            tool, arg = parse_call(rule)
            if tool not in tools:
                continue
            if arg is None:
                hit = (rule, name)
                continue
            if arg.startswith("!"):
                if hit and path_matches(arg[1:], path, kind):
                    hit = None
                continue
            if path_matches(arg, path, kind):
                hit = (rule, name)
        if hit:
            return hit
    return None


def simple_rule(sources, kind, tool, check):
    """Bash, WebFetch 등: kind 목록에서 check(지정자)가 참인 첫 규칙을 찾는다. 지정자가 없으면 모든 사용에 맞는다."""
    for name, perms in sources:
        for rule in perms[kind]:
            rtool, arg = parse_call(rule)
            if rtool == tool and (arg is None or arg == "*" or check(arg)):
                return rule, name
    return None


def is_protected(path):
    path = path.removeprefix("./")
    return path.startswith(PROTECTED_DIRS) or Path(path).name in PROTECTED_FILES


def judge_path(sources, tool, path):
    """Read 또는 Edit 호출 하나를 판정한다."""
    edit = tool in ("Edit", "Write", "NotebookEdit")
    deny_tools = {"Edit", "Read"} if edit else {"Read"}  # Read 거부는 Edit도 막는다
    use_tools = {"Edit"} if edit else {"Read"}
    hit = path_rule(sources, "deny", deny_tools, path)
    if hit:
        return "deny", f"deny 규칙 {hit[0]} ({hit[1]})"
    hit = path_rule(sources, "ask", use_tools, path)
    if hit:
        return "ask", f"ask 규칙 {hit[0]} ({hit[1]})"
    if edit and is_protected(path):
        return "ask", "보호 경로: allow 규칙이 있어도 확인한다"
    hit = path_rule(sources, "allow", use_tools, path)
    if hit:
        return "allow", f"allow 규칙 {hit[0]} ({hit[1]})"
    return ("ask", "기본 동작: 편집은 확인") if edit else ("allow", "기본 동작: 작업 폴더 안 읽기는 허용")


def read_targets(command):
    """cat, head, tail이 이름으로 읽는 파일 목록."""
    try:
        words = shlex.split(command)
    except ValueError:
        return []
    if not words or words[0] not in FILE_READERS:
        return []
    return [w for w in words[1:] if not w.startswith("-") and not w.isdigit()]


def judge_bash_one(sources, command):
    for path in read_targets(command):
        hit = path_rule(sources, "deny", {"Read"}, path)
        if hit:
            return "deny", f"{command}: 파일을 읽는 명령에 Read 거부 {hit[0]} 적용"
    for kind in ("deny", "ask", "allow"):
        hit = simple_rule(sources, kind, "Bash", lambda spec: bash_matches(spec, command))
        if hit:
            return kind, f"{command}: {kind} 규칙 {hit[0]} ({hit[1]})"
    words = command.split()
    if words and (words[0] in READ_ONLY or (words[0] == "git" and len(words) > 1 and words[1] in READ_ONLY_GIT)):
        return "allow", f"{command}: 기본 동작(읽기 전용 명령)"
    return "ask", f"{command}: 기본 동작(맞는 규칙 없음, 확인)"


def judge_bash(sources, command):
    results = [judge_bash_one(sources, part) for part in split_compound(command)]
    for kind in ("deny", "ask"):
        found = [why for k, why in results if k == kind]
        if found:
            return kind, "; ".join(found)
    return "allow", "; ".join(why for _, why in results)


def judge(sources, call):
    """호출 하나를 판정해 (deny|ask|allow, 까닭)을 돌려준다."""
    tool, arg = parse_call(call)
    if tool == "Bash":
        return judge_bash(sources, arg or "")
    if tool in ("Read", "Edit", "Write", "NotebookEdit", "Grep", "Glob"):
        return judge_path(sources, "Read" if tool in ("Grep", "Glob") else tool, arg or ".")
    if tool == "WebFetch":
        domain = (arg or "").removeprefix("domain:")
        def check(spec):
            spec = spec.removeprefix("domain:")
            if spec.startswith("*."):
                return domain.endswith(spec[1:])
            return spec == domain
        for kind in ("deny", "ask", "allow"):
            hit = simple_rule(sources, kind, "WebFetch", check)
            if hit:
                return kind, f"{kind} 규칙 {hit[0]} ({hit[1]})"
        return "ask", "기본 동작: 확인"
    for kind in ("deny", "ask", "allow"):
        hit = simple_rule(sources, kind, tool, lambda spec: False)
        if hit:
            return kind, f"{kind} 규칙 {hit[0]} ({hit[1]})"
    return "ask", "기본 동작: 확인(이 모의기가 다루지 않는 도구)"


LABEL = {"deny": "거부", "ask": "확인", "allow": "허용"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="권한 규칙 판정 모의기(학습용)")
    parser.add_argument("--settings", nargs="+", required=True, help="설정 파일들(낮은 범위부터 적어도 결과는 같다)")
    parser.add_argument("--cases", help="한 줄에 '호출 => 기대'를 적은 파일")
    parser.add_argument("calls", nargs="*", help="판정할 호출(--settings보다 앞에 적는다). 예: \"Bash(git push origin main)\"")
    args = parser.parse_args(argv)
    sources = load_settings(args.settings)

    items = [(call, None) for call in args.calls]
    if args.cases:
        for line in Path(args.cases).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            call, _, expected = line.partition("=>")
            items.append((call.strip(), expected.strip() or None))
    wrong = 0
    for call, expected in items:
        kind, why = judge(sources, call)
        mark = ""
        if expected:
            mark = "  일치" if expected == kind else f"  불일치(기대 {expected})"
            wrong += expected != kind
        print(f"{LABEL[kind]}  {call}{mark}\n      {why}")
    if args.cases:
        print(f"사례 {len(items)}건, 불일치 {wrong}건")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
