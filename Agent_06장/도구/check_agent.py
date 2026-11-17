"""서브에이전트 정의 파일(.claude/agents/*.md)의 프런트매터를 검사한다.

쓰는 법(저장소 폴더에서):
    python ~/kits/Agent_06장/도구/check_agent.py .claude/agents/reviewer.md --read-only

검사하는 것(Claude Code 문서 「Create custom subagents」, 2026-11-14 확인):
- 파일의 첫 줄이 '---'이고 프런트매터가 '---'로 닫힌다. 아니면 Claude Code가 파일을 조용히 건너뛴다.
- name과 description이 있다(필수). name에는 ':'이 없고 '-'로 시작하지 않으며 256자 이하이다.
- 알려진 필드만 쓴다. 모르는 필드는 Claude Code가 조용히 무시하므로 철자 오류를 경고한다.
- tools가 없으면 모든 도구를 물려받는다는 경고를 낸다.
- --read-only를 주면 tools가 읽기 도구(Read, Grep, Glob)로만 되어 있는지 본다.
- 본문(시스템 프롬프트)이 비어 있지 않다.
PyYAML 없이 이 과목에서 쓰는 단순한 꼴(키: 값, 목록은 쉼표 또는 '- ' 줄)만 읽는다.
"""

import sys
from pathlib import Path

KNOWN = {
    "name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns",
    "autoCompactWindow", "skills", "mcpServers", "hooks", "memory", "background", "omitClaudeMd",
    "effort", "isolation", "color", "initialPrompt", "experimental",
}
READ_ONLY = {"Read", "Grep", "Glob"}
MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}


def parse(text):
    """(프런트매터 dict, 본문)을 돌려준다. 프런트매터가 없으면 (None, text)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, text
    data, key = {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):          # 앞 키에 딸린 줄(목록 항목이나 중첩)
            item = raw.strip()
            if key and item.startswith("- ") and isinstance(data.get(key), list):
                data[key].append(item[2:].strip().strip("\"'"))
            continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            data[key] = []                      # 다음 줄부터 목록이나 중첩이 온다
        else:
            data[key] = value.strip("\"'")
    return data, "\n".join(lines[end + 1:])


def as_list(value):
    if isinstance(value, list):
        return [v for v in value if v]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def check(path, read_only):
    problems, warnings = [], []
    data, body = parse(path.read_text(encoding="utf-8"))
    if data is None:
        return ["첫 줄이 '---'인 프런트매터가 없다(Claude Code가 이 파일을 건너뛴다)"], warnings
    name = data.get("name")
    if not name:
        problems.append("name이 없다")
    elif isinstance(name, str) and (":" in name or name.startswith("-") or len(name) > 256):
        problems.append(f"name이 규칙에 맞지 않는다: {name!r}")
    if not data.get("description"):
        problems.append("description이 없다(Claude Code가 이 파일을 건너뛴다)")
    for key in data:
        if key not in KNOWN:
            warnings.append(f"알려지지 않은 필드 '{key}'는 무시된다(철자를 확인한다)")
    tools = as_list(data["tools"]) if "tools" in data else None
    if tools is None:
        warnings.append("tools가 없어 모든 도구를 물려받는다")
    model = data.get("model")
    if isinstance(model, str) and model not in MODELS and not model.startswith("claude-"):
        warnings.append(f"model 값 '{model}'을 확인한다(sonnet, opus, haiku, fable, inherit, 전체 모델 ID)")
    if read_only:
        if tools is None:
            problems.append("--read-only: tools를 적지 않으면 쓰기 도구까지 물려받는다")
        else:
            extra = [t for t in tools if t not in READ_ONLY]
            if extra:
                problems.append(f"--read-only: 읽기 도구가 아닌 것이 있다: {', '.join(extra)}")
    if not body.strip():
        problems.append("본문(시스템 프롬프트)이 비어 있다")
    return problems, warnings


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    read_only = "--read-only" in sys.argv
    if not args:
        sys.exit("쓰는 법: python check_agent.py <정의 파일> [--read-only]")
    failed = False
    for arg in args:
        path = Path(arg)
        problems, warnings = check(path, read_only)
        data, _ = parse(path.read_text(encoding="utf-8"))
        tools = ", ".join(as_list(data.get("tools", []))) if data and "tools" in data else "(모든 도구)"
        print(f"{path}: name={data.get('name') if data else None}  tools={tools}")
        for line in problems:
            print("  문제:", line)
        for line in warnings:
            print("  경고:", line)
        if problems:
            failed = True
        else:
            print("  통과")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
