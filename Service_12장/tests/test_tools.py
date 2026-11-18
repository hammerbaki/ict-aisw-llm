"""키트 도구의 검사. 키트 폴더에서 `python -m pytest -q`로 돈다."""
import os
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TOOLS = KIT / "도구"
PRACTICE = KIT / "연습"


def run(tool, *args):
    e = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, str(TOOLS / tool), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", env=e, cwd=KIT)
    return p.returncode, p.stdout + p.stderr


def test_spec_checklist_example():
    code, out = run("spec_checklist.py", PRACTICE / "점검표_A.md")
    assert code == 0 and "충족 3 · 부분 0 · 미충족 1" in out and "충족률 75.0%" in out


def test_spec_checklist_partial_and_na(tmp_path):
    f = tmp_path / "b.md"
    rows = ["| ID | 판정 |", "|---|---|", "| REQ-01 | 충족 |", "| REQ-02 | 부분 |",
            "| REQ-03 | 해당없음 |", "| REQ-04 | 미충족 |"]
    f.write_text("\n".join(rows) + "\n", encoding="utf-8")
    code, out = run("spec_checklist.py", f)
    assert code == 0 and "충족률 50.0%" in out  # (1 + 0.5) / (4 - 1)


def test_spec_checklist_unknown_label(tmp_path):
    f = tmp_path / "bad.md"
    f.write_text("| ID | 판정 |\n|---|---|\n| REQ-01 | 거의 |\n", encoding="utf-8")
    code, out = run("spec_checklist.py", f)
    assert code == 1 and "판정을 읽지 못함" in out


def test_templates_have_no_old_case():
    for f in KIT.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        assert "jobprep" not in text and "자기소개서" not in text, f.name
