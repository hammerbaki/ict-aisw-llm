"""11장의 보안 설정(거부 규칙과 PreToolUse 훅)을 저장소의 .claude/settings.json에 합친다.

- permissions.deny: 없는 규칙만 뒤에 덧붙인다. 이미 있는 규칙과 그 순서는 건드리지 않는다.
- hooks: 같은 command가 아직 없는 묶음만 덧붙인다. 6장의 보호 파일 훅, 편집 뒤 테스트 훅은 그대로 둔다.
- 원래 파일은 settings.json.bak으로 남긴다. --check는 고치지 않고 빠진 것만 보고한다(빠졌으면 종료 코드 1).

    python ~/kits/Agent_11장/도구/merge_security.py --check
    python ~/kits/Agent_11장/도구/merge_security.py
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

SNIPPET = Path(__file__).resolve().parent.parent / "settings_보안추가.json"


def plan(settings, snippet):
    """덧붙일 (deny 규칙 목록, [(이벤트, 묶음)] 목록)을 돌려준다."""
    have_deny = settings.get("permissions", {}).get("deny", [])
    new_deny = [r for r in snippet["permissions"]["deny"] if r not in have_deny]
    new_groups = []
    for event, groups in snippet.get("hooks", {}).items():
        existing = settings.get("hooks", {}).get(event, [])
        commands = {h.get("command") + "|" + g.get("matcher", "") for g in existing for h in g.get("hooks", [])}
        for group in groups:
            keys = {h.get("command") + "|" + group.get("matcher", "") for h in group.get("hooks", [])}
            if not keys <= commands:
                new_groups.append((event, group))
    return new_deny, new_groups


def main(argv=None):
    parser = argparse.ArgumentParser(description="11장 보안 설정 합치기")
    parser.add_argument("--settings", default=".claude/settings.json")
    parser.add_argument("--snippet", default=str(SNIPPET))
    parser.add_argument("--check", action="store_true", help="고치지 않고 빠진 것만 보고한다")
    args = parser.parse_args(argv)
    path = Path(args.settings)
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    snippet = json.loads(Path(args.snippet).read_text(encoding="utf-8"))
    new_deny, new_groups = plan(settings, snippet)

    for rule in new_deny:
        print(f"{'빠짐' if args.check else '더함'}  deny {rule}")
    for event, group in new_groups:
        print(f"{'빠짐' if args.check else '더함'}  hooks.{event} matcher={group.get('matcher')}")
    if args.check:
        print("보안 설정: 모두 있음" if not (new_deny or new_groups) else "보안 설정: 빠진 것이 있다")
        return 1 if (new_deny or new_groups) else 0
    if not (new_deny or new_groups):
        print("이미 모두 있다. 고치지 않았다.")
        return 0
    if path.exists():
        shutil.copyfile(path, path.with_name(path.name + ".bak"))
    settings.setdefault("permissions", {}).setdefault("deny", []).extend(new_deny)
    for event, group in new_groups:
        settings.setdefault("hooks", {}).setdefault(event, []).append(group)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"고침: {path.as_posix()} (이전 판: {path.name}.bak)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
