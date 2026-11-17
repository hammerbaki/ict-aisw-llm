"""회귀 판정의 테스트: 합격선과 기준선에 따라 종료 코드가 정해지는가."""

import json

import pytest

from evals import gate


def write_run(tmp_path, pass_rate, judge=0.95):
    summary = {"tag": "t", "created": "2027-11-01T00:00:00", "model": "sim-a", "runs": 5,
               "prompts": {"summary": "summary_v3", "ask": "ask_v1"},
               "suites": {"summary": {"pass_rate": pass_rate,
                                      "criteria": {"structure": 1.0, "judge": judge}}}}
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return run_dir


@pytest.fixture
def config(tmp_path, monkeypatch):
    thresholds = {"min_runs": 3, "max_drop_from_baseline": 0.05,
                  "summary": {"min_pass_rate": 0.8, "min_criteria": {"structure": 0.95, "judge": 0.9}}}
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(thresholds), encoding="utf-8")
    monkeypatch.setattr(gate, "THRESHOLDS", path)
    monkeypatch.setattr(gate, "BASELINE", tmp_path / "baseline.json")
    return tmp_path


def test_pass_returns_zero(config):
    assert gate.main([str(write_run(config, 0.9))]) == 0


def test_below_threshold_returns_one(config):
    assert gate.main([str(write_run(config, 0.7))]) == 1


def test_criterion_below_threshold_returns_one(config):
    assert gate.main([str(write_run(config, 0.9, judge=0.8))]) == 1


def test_drop_from_baseline_returns_one(config):
    (config / "baseline.json").write_text(json.dumps({"suites": {"summary": {"pass_rate": 0.97}}}), encoding="utf-8")
    assert gate.main([str(write_run(config, 0.9))]) == 1


def test_update_baseline_only_when_passing(config):
    run_dir = write_run(config, 0.9)
    assert gate.main([str(run_dir), "--update-baseline"]) == 0
    saved = json.loads((config / "baseline.json").read_text(encoding="utf-8"))
    assert saved["suites"]["summary"]["pass_rate"] == 0.9
