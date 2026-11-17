"""판정자 보정 도구의 테스트."""

from evals import judge
from evals.calibrate import cohen_kappa


def test_kappa_is_one_for_perfect_agreement_and_zero_for_chance():
    perfect = [("pass", "pass"), ("fail", "fail")] * 3
    assert cohen_kappa(perfect) == 1.0
    chance = [("pass", "pass"), ("pass", "fail"), ("fail", "pass"), ("fail", "fail")]
    assert abs(cohen_kappa(chance)) < 1e-9


def test_mock_judge_flags_invented_sentence():
    evidence = "- 접수 마감: 2027-10-10 18:00\n- 면접 일정은 개별 문자로 안내한다"
    assert judge.mock_judge(evidence, "면접 일정은 개별 문자로 안내한다")[0] == "pass"
    assert judge.mock_judge(evidence, "회사 홈페이지에서 인재상을 확인한다")[0] == "fail"


def test_number_check_catches_changed_number():
    evidence = "- 수습 기간 3개월 동안 급여의 90%를 지급한다"
    changed = "수습 기간 3개월 동안 급여의 100%를 지급한다"
    assert judge.mock_judge(evidence, changed)[0] == "pass"
    assert judge.mock_judge(evidence, changed, check_numbers=True)[0] == "fail"


def test_swap_check_returns_tie_when_orders_disagree():
    always_first = lambda evidence, a, b: "first"  # noqa: E731  순서만 보는 판정자
    assert judge.swap_check("", "x", "y", judge_fn=always_first) == "tie"
