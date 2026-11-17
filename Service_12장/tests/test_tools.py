"""키트 도구의 검사. 키트 폴더에서 `pytest -q`로 돈다(모의 모드, 서버 없이)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TOOLS = KIT / "도구"
PRACTICE = KIT / "연습"


def run(tool, *args, env=None):
    e = {**os.environ, "LLM_FAKE": "1", "EMBED_BACKEND": "fallback", "PYTHONIOENCODING": "utf-8", **(env or {})}
    p = subprocess.run([sys.executable, str(TOOLS / tool), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", env=e, cwd=KIT)
    return p.returncode, p.stdout + p.stderr


def base_copy(tmp_path, index=False):
    dest = tmp_path / "jobprep"
    shutil.copytree(KIT / "기준산출물" / "jobprep", dest,
                    ignore=shutil.ignore_patterns("__pycache__", "logs", ".pytest_cache", "index"))
    if index:  # 11장의 질의응답은 색인이 있어야 답한다(대체 임베딩으로 만든다)
        e = {**os.environ, "EMBED_BACKEND": "fallback", "PYTHONIOENCODING": "utf-8"}
        subprocess.run([sys.executable, "-m", "rag", "index"], cwd=dest, env=e, check=True, capture_output=True)
    return dest


def test_check_common_fails_before_implementation(tmp_path):
    code, out = run("check_common.py", "--app-dir", base_copy(tmp_path), "--adapter", KIT / "검사어댑터" / "form.json")
    assert code == 1
    assert "경로 /api/feedback가 없다" in out and "통과 0/5" in out


def test_measure_latency_in_process(tmp_path):
    app = base_copy(tmp_path, index=True)
    log = tmp_path / "calls.jsonl"
    code, out = run("measure_latency.py", "--app-dir", app, "--scenario", PRACTICE / "시나리오_ask.json",
                    "--repeat", 3, "--out", tmp_path / "t.csv", env={"LLM_LOG_PATH": str(log)})
    assert code == 0, out
    assert "과업당 요청 2회" in out and "중앙값" in out
    assert len(log.read_text(encoding="utf-8").splitlines()) == 8  # (준비 1 + 반복 3) × 2


def test_token_report_example():
    code, out = run("token_report.py", PRACTICE / "호출기록_예시.jsonl", "--tasks", 2, "--price-in", 1, "--price-out", 5)
    assert code == 0
    assert "| A (모의·어림) | 2 | 0 | 450 | 118 | 1.0 | 284 |" in out
    assert "| B (모의·어림) | 4 | 1 | 900 | 183 |" in out


def test_spec_checklist_example():
    code, out = run("spec_checklist.py", PRACTICE / "점검표_A.md")
    assert code == 0 and "충족률 75.0%" in out


def test_spec_checklist_unknown_label(tmp_path):
    f = tmp_path / "bad.md"
    f.write_text("| ID | 판정 |\n|---|---|\n| REQ-080 | 거의 |\n", encoding="utf-8")
    code, out = run("spec_checklist.py", f)
    assert code == 1 and "판정을 읽지 못함" in out


def test_spec_diff_example():
    code, out = run("spec_diff.py", PRACTICE / "원명세_마감표시.md",
                    f"A={PRACTICE / '추출명세_A.md'}", f"B={PRACTICE / '추출명세_B.md'}")
    assert code == 0
    assert "원 명세 요구 4개" in out
    assert "| DL-04 | (없음) | B-03 |" in out
    assert "A-04" in out and "B-04" in out and "B-05" in out


def test_spec_diff_range_filters(tmp_path):
    spec = tmp_path / "s.md"
    spec.write_text("| ID | 요구 |\n|---|---|\n| REQ-001 | a |\n| REQ-080 | b |\n| REQ-081 | c |\n| REQ-090 | d |\n", encoding="utf-8")
    ext = tmp_path / "e.md"
    ext.write_text("| ID | 요구 | 대응 |\n|---|---|---|\n| X-01 | b | REQ-080 |\n", encoding="utf-8")
    code, out = run("spec_diff.py", spec, f"x={ext}", "--range", "REQ-080~089")
    assert "원 명세 요구 2개" in out and "REQ-081" in out.split("[1]")[1].split("[2]")[0]


def test_prepare_base(tmp_path):
    code, out = run("prepare_base.py", tmp_path)
    assert code == 0 and (tmp_path / "jobprep" / "api" / "app.py").exists()
    code, out = run("prepare_base.py", tmp_path)
    assert "복사 0개" in out


def test_adapters_and_scenarios_are_valid_json():
    for p in list((KIT / "검사어댑터").glob("*.json")) + list((KIT / "시나리오").glob("*.json")):
        json.loads(p.read_text(encoding="utf-8"))
