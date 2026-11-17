"""11장: 간접 프롬프트 주입 재현과 대책의 회귀 테스트.

저장소의 대책(.claude/settings.json의 거부 규칙, .claude/hooks/block_secrets.py, .claude/agents/issue-triage.md)을
임시 폴더에 복사하고, 그곳에 테스트마다 새 가짜 키를 만들어 가짜 에이전트(security/lab/naive_agent.py)를 돌린다.
저장소의 secrets/와 security/out/은 건드리지 않는다. 대책을 적용하기 전에는 「막혀야 한다」는 테스트가 실패한다.
"""

import json
import secrets
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "security" / "lab"
sys.path.insert(0, str(LAB))
import naive_agent  # noqa: E402

SCENARIOS = ["issue_42.md", "issue_43_우회.md", "job_31.json", "자료_07_현장실습_추가안내.md"]
DEFENSE_FILES = [".claude/settings.json", ".claude/hooks/block_secrets.py", ".claude/agents/issue-triage.md"]
LAYER_FILES = {"rules": DEFENSE_FILES[:1], "hook": DEFENSE_FILES[1:2], "tools": DEFENSE_FILES[2:], "output": []}

# 방어층 하나만 켰을 때 막혀야 하는 시나리오. 여기에 없는 칸(예: rules만으로 issue_43_우회)은
# 그 층 하나로는 막지 못하는 경로이며, 강의안 7절의 표에서 까닭을 다룬다.
BLOCKED_BY_ONE_LAYER = [
    ("rules", "issue_42.md"),
    ("rules", "job_31.json"),
    ("rules", "자료_07_현장실습_추가안내.md"),
    ("hook", "issue_42.md"),
    ("hook", "issue_43_우회.md"),
    ("hook", "job_31.json"),
    ("hook", "자료_07_현장실습_추가안내.md"),
    ("tools", "issue_43_우회.md"),
    ("tools", "job_31.json"),
    ("tools", "자료_07_현장실습_추가안내.md"),
    ("output", "issue_42.md"),
    ("output", "issue_43_우회.md"),
    ("output", "job_31.json"),
    ("output", "자료_07_현장실습_추가안내.md"),
]


@pytest.fixture
def lab(tmp_path):
    for rel in DEFENSE_FILES:
        src = ROOT / rel
        if src.exists():
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, tmp_path / rel)
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(LAB, tmp_path / "security" / "lab", ignore=ignore)
    shutil.copytree(ROOT / "security" / "tools", tmp_path / "security" / "tools", ignore=ignore)
    key = "LABKEY-" + secrets.token_hex(16)
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "실습용_가짜키.txt").write_text(f"JOBPREP_LAB_KEY={key}\n", encoding="utf-8")
    return tmp_path


def attack(root, scenario, defenses, **kwargs):
    kwargs.setdefault("log_dir", None)
    return naive_agent.run(f"security/lab/scenarios/{scenario}", defenses, root=root, quiet=True, **kwargs)


def need(root, *rels):
    missing = [r for r in rels if not (root / r).exists()]
    if missing:
        pytest.fail(f"대책 파일이 없다: {', '.join(missing)} (강의안 11절)")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_attack_succeeds_without_defense(lab, scenario):
    """방어가 없으면 순진한 에이전트는 문서 속 지시를 따라 가짜 키를 내보낸다(공격 경로가 살아 있다)."""
    summary = attack(lab, scenario, [])
    assert summary["leaked"], summary
    assert summary["injected_steps"] == 2


@pytest.mark.parametrize("layer,scenario", BLOCKED_BY_ONE_LAYER)
def test_single_layer_blocks(lab, layer, scenario):
    need(lab, *LAYER_FILES[layer])
    summary = attack(lab, scenario, [layer])
    assert not summary["leaked"], summary
    assert layer in summary["blocked_layers"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_all_layers_block_every_scenario(lab, scenario):
    need(lab, *DEFENSE_FILES)
    summary = attack(lab, scenario, list(naive_agent.LAYERS))
    assert not summary["leaked"], summary


def test_careful_human_stops_interpreter_bypass(lab):
    """규칙에 걸리지 않는 우회(python -c)는 확인 창으로 간다. 사람이 거절하면 막힌다."""
    need(lab, ".claude/settings.json")
    assert attack(lab, "issue_43_우회.md", ["rules"], ask="approve")["leaked"]
    assert not attack(lab, "issue_43_우회.md", ["rules"], ask="deny")["leaked"]


def test_audit_log_has_decisions_and_no_secret(lab):
    need(lab, *LAYER_FILES["hook"])
    attack(lab, "issue_42.md", ["hook"], log_dir="security/logs")
    log = lab / "security" / "logs" / "issue_42__hook.jsonl"
    lines = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    key = (lab / "secrets" / "실습용_가짜키.txt").read_text(encoding="utf-8").split("=")[1].strip()
    assert key not in log.read_text(encoding="utf-8")
    calls = [l for l in lines if "tool" in l]
    assert {"time", "tool", "input", "decision", "layer", "reason"} <= set(calls[0])
    assert any(c["decision"] == "막힘" and c["layer"] == "hook" for c in calls)
    assert lines[-1]["summary"]["leaked"] is False
