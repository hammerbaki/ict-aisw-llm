# -*- coding: utf-8 -*-
"""settings_MCP규칙.json의 규칙을 저장소의 .claude/settings.json에 더한다(5장 9-8절).

이미 있는 규칙은 다시 넣지 않고, 다른 키(hooks 등)는 그대로 둔다. 저장소 폴더에서 실행한다.
    python ~/kits/Agent_05장/설정/merge_settings.py
"""
import json
from pathlib import Path

target = Path(".claude/settings.json")
rules = json.loads((Path(__file__).parent / "settings_MCP규칙.json").read_text(encoding="utf-8"))
settings = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
permissions = settings.setdefault("permissions", {})
added = []
for kind, items in rules["permissions"].items():
    current = permissions.setdefault(kind, [])
    for rule in items:
        if rule not in current:
            current.append(rule)
            added.append(f"{kind}: {rule}")
target.parent.mkdir(exist_ok=True)
# 바이트로 쓴다. Windows에서 write_text가 줄 끝을 CRLF로 바꾸지 않게 한다(저장소의 텍스트는 LF).
target.write_bytes((json.dumps(settings, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
print("더한 규칙:", *added, sep="\n  ") if added else print("더할 규칙이 없다(이미 모두 있다).")
