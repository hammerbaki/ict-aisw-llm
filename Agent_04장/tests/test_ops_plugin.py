# -*- coding: utf-8 -*-
"""4장 3단계: 플러그인 jobprep-ops와 팀 마켓플레이스 jobprep-team의 구조 테스트.

공식 검사는 `claude plugin validate`가 한다. 이 테스트는 그 명령이 없는 곳(CI 등)에서도
같은 실수(이름 불일치, 잘못된 위치, 버전 이중 기재)를 잡기 위한 최소한의 확인이다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "jobprep-ops"
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"
MARKET = ROOT / ".claude-plugin" / "marketplace.json"


def load(path):
    assert path.exists(), f"{path.relative_to(ROOT)}가 없다"
    return json.loads(path.read_text(encoding="utf-8"))


def test_매니페스트에_이름과_버전이_있다():
    m = load(MANIFEST)
    assert m["name"] == "jobprep-ops"
    assert re.fullmatch(r"\d+\.\d+\.\d+", m.get("version", "")), "version은 0.1.0 꼴로 적는다"
    assert m.get("author", {}).get("name"), "author.name이 없다"


def test_구성_요소는_claude_plugin_폴더_밖에_있다():
    inside = {p.name for p in (PLUGIN / ".claude-plugin").iterdir()}
    assert inside == {"plugin.json"}, f".claude-plugin/에는 plugin.json만 둔다: {sorted(inside)}"
    assert (PLUGIN / "skills" / "incident-report" / "SKILL.md").exists()


def test_스킬은_한_곳에만_있다():
    assert not (ROOT / ".claude" / "skills" / "incident-report").exists(), \
        ".claude/skills/incident-report가 남아 있으면 /incident-report와 /jobprep-ops:incident-report가 함께 뜬다"


def test_마켓플레이스_항목이_플러그인을_가리킨다():
    mk = load(MARKET)
    assert mk["name"] == "jobprep-team"
    assert mk["owner"]["name"]
    entry = next(p for p in mk["plugins"] if p["name"] == "jobprep-ops")
    assert entry["name"] == load(MANIFEST)["name"], "항목 이름과 매니페스트 이름을 같게 둔다"
    assert entry["source"].startswith("./") and ".." not in entry["source"]
    assert (ROOT / entry["source"]).resolve() == PLUGIN.resolve()
    assert "version" not in entry, "버전은 plugin.json 한 곳에만 적는다"
