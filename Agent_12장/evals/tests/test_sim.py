"""변동 모의 모델의 테스트: 결정적인가, 판본(규칙 문장)에 반응하는가."""

import json

from api import llm
from evals import sim
from evals.run import load_golden


def summary_prompt(version, job_text):
    system, template = llm.load_prompt(version)
    return system, llm.fill(template, {"JOB_TEXT": job_text})


def test_same_condition_gives_same_text():
    job = load_golden("summary")[0]["input"]
    system, prompt = summary_prompt("summary_v1", job)
    first = sim.make_complete("sim-a", 0)(system, prompt, "summary")
    again = sim.make_complete("sim-a", 0)(system, prompt, "summary")
    assert first == again


def test_different_runs_can_differ():
    job = load_golden("summary")[0]["input"]
    system, prompt = summary_prompt("summary_v1", job)
    texts = {sim.make_complete("sim-a", run)(system, prompt, "summary") for run in range(20)}
    assert len(texts) > 1


def test_preferred_rule_reduces_mixing():
    """우대 사항 규칙이 있는 v2는 v1보다 우대 사항을 자격 요건에 덜 섞는다."""
    jobs = [i for i in load_golden("summary") if i["expect"]["preferred"]]

    def mixed(version):
        count = 0
        for run in range(10):
            complete = sim.make_complete("sim-a", run)
            for i in jobs:
                text = complete(*summary_prompt(version, i["input"]), "summary")
                try:
                    data = json.loads(text.strip("`").removeprefix("json").strip())
                except json.JSONDecodeError:
                    continue
                count += any(p in data["qualifications"] for p in i["expect"]["preferred"])
        return count

    assert mixed("summary_v2") < mixed("summary_v1")


def test_unknown_model_name_is_rejected():
    try:
        sim.make_complete("claude-real", 0)
    except ValueError as error:
        assert "모의 모델" in str(error)
    else:
        raise AssertionError("ValueError가 나야 한다")
