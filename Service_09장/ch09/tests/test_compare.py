"""판본 비교 실행기: 모의 응답으로 끝까지 돌고, 결과 파일을 남긴다."""
import json

import pytest

from eval import run_compare


def test_compare_fake(tmp_path, capsys):
    assert run_compare.main(["v1", "v2", "v3", "--out", str(tmp_path)]) == 0
    totals = {v: json.loads((tmp_path / v / "summary.json").read_text(encoding="utf-8"))["합계"]
              for v in ("v1", "v2", "v3")}
    assert totals["v1"] < totals["v2"] < totals["v3"] <= 50
    assert (tmp_path / "비교표.md").exists()
    meta = json.loads((tmp_path / "v3" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["모의"] is True and meta["문항수"] == 10
    assert "모의 응답 재생" in capsys.readouterr().out


def test_refuses_to_overwrite(tmp_path):
    run_compare.main(["v1", "--out", str(tmp_path)])
    assert run_compare.main(["v1", "--out", str(tmp_path)]) == 2
    assert run_compare.main(["v1", "--out", str(tmp_path), "--overwrite"]) == 0
    assert any((tmp_path / "_이전").iterdir())


def test_new_version_needs_real_call(tmp_path, monkeypatch):
    """모의 응답이 없는 새 판본(v4)은 모의 모드에서 잴 수 없다고 알리고 멈춘다."""
    from api.prompts import load_prompt
    monkeypatch.setattr(run_compare, "load_prompt", lambda v: load_prompt("v3"))
    with pytest.raises(SystemExit, match="실제 호출"):
        run_compare.main(["v4", "--out", str(tmp_path / "r")])


def test_failure_leaves_no_partial_result(tmp_path, monkeypatch):
    """실제 호출이 중간에 실패하면 결과 폴더를 남기지 않는다(반쯤 찬 결과로 비교하지 않게)."""
    monkeypatch.setenv("LLM_FAKE", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="키가 없다"):
        run_compare.main(["v1", "--out", str(tmp_path)])
    assert not any(tmp_path.iterdir())
