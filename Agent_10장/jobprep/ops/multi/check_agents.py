"""check_agents: .claude/agents/의 역할 에이전트 정의 파일을 검사한다.

Claude Code는 알 수 없는 프런트매터 필드를 오류 없이 무시한다(2026-11 문서 기준). 그래서 `allowed-tools`처럼
철자를 틀린 필드는 아무 경고 없이 효과가 없어진다. 이 검사기는 그런 실수를 실행 전에 찾는다.
모델을 부르지 않고 파일만 읽는다. Claude Code가 실제로 정의를 읽는지는 대화로 확인한다(v2.1.198 이후의 /agents는 안내 문장만 낸다).

사용법 (저장소 맨 위에서)
    python ops/multi/check_agents.py                 # .claude/agents/*.md 전부
    python ops/multi/check_agents.py planner reviewer
검사: ① 프런트매터가 ---로 열리고 닫힌다 ② name과 description이 있다 ③ name이 파일 이름과 같다
     ④ 알려진 필드만 쓴다 ⑤ model, permissionMode, isolation의 값이 허용된 값이다 ⑥ 본문(지시문)이 비어 있지 않다
종료 코드: 오류가 없으면 0, 있으면 1. 경고(알 수 없는 도구 이름 등)는 종료 코드에 넣지 않는다.
"""

import sys
from pathlib import Path

KNOWN_FIELDS = {
    "name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns",
    "autoCompactWindow", "skills", "mcpServers", "hooks", "memory", "background", "omitClaudeMd",
    "effort", "isolation", "color", "initialPrompt", "experimental",
}
MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
PERMISSION_MODES = {"default", "manual", "acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan"}
KNOWN_TOOLS = {"Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebFetch", "WebSearch", "Agent", "Task",
               "NotebookEdit", "TodoWrite", "Skill", "Monitor", "PowerShell"}


def parse(path):
    """프런트매터(키: 값)와 본문을 돌려준다. 들여쓴 줄(목록, 중첩)은 바로 위 키의 값에 붙인다."""
    lines = path.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0].strip() != "---":
        return None, None
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return None, None
    fields, key = {}, None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t-" and key:
            fields[key] += " " + line.strip()
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            fields[key] = value.strip()
    return fields, "\n".join(lines[end + 1:]).strip()


def check(path):
    errors, warnings = [], []
    fields, body = parse(path)
    if fields is None:
        return [f"{path}: 프런트매터가 ---로 열리고 닫히지 않는다"], []
    for required in ("name", "description"):
        if not fields.get(required):
            errors.append(f"{path}: 필수 필드 {required}가 없다")
    if fields.get("name") and fields["name"] != path.stem:
        warnings.append(f"{path}: name({fields['name']})이 파일 이름({path.stem})과 다르다. 호출은 name으로 한다")
    for key in fields:
        if key not in KNOWN_FIELDS:
            errors.append(f"{path}: 알 수 없는 필드 {key} (Claude Code는 오류 없이 무시한다)")
    model = fields.get("model")
    if model and model not in MODELS and not model.startswith("claude-"):
        errors.append(f"{path}: model 값 {model}은 별칭(sonnet, opus, haiku, fable, inherit)이나 claude-로 시작하는 이름이 아니다")
    mode = fields.get("permissionMode")
    if mode and mode not in PERMISSION_MODES:
        errors.append(f"{path}: permissionMode 값 {mode}은 허용된 값이 아니다")
    if fields.get("isolation") and fields["isolation"] != "worktree":
        errors.append(f"{path}: isolation의 값은 worktree뿐이다")
    for key in ("tools", "disallowedTools"):
        for tool in [t.strip(" -") for t in fields.get(key, "").replace(",", " ").split()]:
            base = tool.split("(")[0]
            if base and base not in KNOWN_TOOLS and not base.startswith("mcp__") and ")" not in tool:
                warnings.append(f"{path}: {key}의 {tool}은 이 검사기가 모르는 도구 이름이다")
        if key == "disallowedTools" and "(" in fields.get(key, ""):
            warnings.append(f"{path}: disallowedTools에 Bash(...)처럼 조건을 붙이면 그 도구 전체가 빠진다(문서). "
                            "명령 단위로 막으려면 settings.json의 permissions.deny를 쓴다")
    if not body:
        errors.append(f"{path}: 본문(시스템 프롬프트)이 비었다")
    return errors, warnings


def main(argv):
    folder = Path(".claude/agents")
    paths = [folder / f"{name}.md" for name in argv] if argv else sorted(folder.glob("*.md"))
    all_errors = []
    for path in paths:
        if not path.exists():
            all_errors.append(f"{path}: 파일이 없다")
            continue
        errors, warnings = check(path)
        fields, _ = parse(path)
        summary = f"tools={fields.get('tools', '(전부 상속)')} model={fields.get('model', '(상속)')}" if fields else ""
        print(f"{'오류' if errors else '통과'}  {path.as_posix()}  {summary}")
        for message in warnings:
            print(f"  경고: {message}")
        for message in errors:
            print(f"  오류: {message}")
        all_errors += errors
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
