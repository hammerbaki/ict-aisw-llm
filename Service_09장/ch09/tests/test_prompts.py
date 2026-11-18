"""프롬프트 판본 파일은 형식을 지키고, 판본마다 한 가지씩만 다른가."""
import pytest

from api.prompts import PLACEHOLDER, load_prompt


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
def test_prompt_loads(version):
    p = load_prompt(version)
    assert p.version == version and p.note
    assert "<공고>" not in p.render("본문") or "본문" in p.render("본문")
    assert PLACEHOLDER not in p.render("본문")


def test_v2_adds_rules():
    v1, v2 = load_prompt("v1"), load_prompt("v2")
    assert "null" not in v1.system and "null" in v2.system
    assert "<규칙>" in v2.system


def test_v3_is_v2_plus_examples():
    v2, v3 = load_prompt("v2"), load_prompt("v3")
    assert "<예시>" in v3.system and "<예시>" not in v2.system
    without_examples = v3.system.split("<예시>")[0] + v3.system.split("</예시>")[1]
    assert without_examples.split() == v2.system.split()
    assert v2.user_template == v3.user_template


def test_missing_prompt():
    with pytest.raises(FileNotFoundError):
        load_prompt("v99")
