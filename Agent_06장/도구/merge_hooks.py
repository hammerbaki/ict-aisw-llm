"""설정 파일(.claude/settings.json 등)에 훅 설정 조각을 합친다.

쓰는 법(저장소 폴더에서):
    python ~/kits/Agent_06장/도구/merge_hooks.py .claude/settings.json ~/kits/Agent_06장/훅설정.json

- 설정 파일의 다른 키(permissions 등)는 그대로 둔다.
- 조각의 hooks에 있는 이벤트마다 matcher 그룹을 더한다. 같은 command가 이미 있으면 더하지 않는다.
- 설정 파일이 없으면 새로 만든다. 사본을 남기지 않으므로, 되돌릴 때는 git restore를 쓴다.
- 표준 라이브러리만 쓴다.
"""

import json
import sys
from pathlib import Path


def load(path):
    """JSON 파일을 읽는다. 문법 오류가 있으면 줄과 칸을 알려 주고 멈춘다."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        sys.exit(f"{path}: JSON 문법 오류 ({error.lineno}번째 줄, {error.colno}번째 칸): {error.msg}")


def commands(groups):
    """matcher 그룹 목록에 들어 있는 command 문자열의 집합."""
    found = set()
    for group in groups:
        for handler in group.get("hooks", []):
            if "command" in handler:
                found.add(handler["command"])
    return found


def merge(settings, piece):
    """piece의 hooks를 settings의 hooks에 합치고, 더한 항목의 설명 목록을 돌려준다."""
    added = []
    hooks = settings.setdefault("hooks", {})
    for event, groups in piece.get("hooks", {}).items():
        current = hooks.setdefault(event, [])
        existing = commands(current)
        for group in groups:
            new_handlers = [h for h in group.get("hooks", []) if h.get("command") not in existing]
            if not new_handlers:
                continue
            new_group = dict(group)
            new_group["hooks"] = new_handlers
            current.append(new_group)
            for handler in new_handlers:
                added.append(f"{event} [{group.get('matcher', '*')}] {handler.get('command')}")
    return added


def main():
    if len(sys.argv) != 3:
        sys.exit("쓰는 법: python merge_hooks.py <설정 파일> <훅 설정 조각>")
    target, piece_path = Path(sys.argv[1]), Path(sys.argv[2])
    piece = load(piece_path)
    if target.exists():
        settings = load(target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        settings = {}
    added = merge(settings, piece)
    target.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")  # Windows에서도 LF로 쓴다
    if added:
        print(f"{target}에 훅 {len(added)}개를 더하였다.")
        for line in added:
            print("  +", line)
    else:
        print(f"{target}: 더할 훅이 없다(이미 모두 있다).")


if __name__ == "__main__":
    main()
