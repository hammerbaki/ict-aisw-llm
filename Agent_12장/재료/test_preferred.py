"""우대 사항 혼입 채점기(grade_preferred)의 테스트. 12장 11-2에서 evals/tests/로 복사한다."""

from evals import graders


def item(preferred):
    return {"id": "T", "suite": "regression",
            "expect": {"deadline": None, "duties": [], "qualifications": ["SQL 기초 문법을 아는 사람"],
                       "cautions": [], "preferred": preferred}}


def test_preferred_mixed_into_qualifications_fails():
    output = {"qualifications": ["SQL 기초 문법을 아는 사람", "데이터 시각화 도구 사용 경험"]}
    ok, note = graders.grade_preferred(item(["데이터 시각화 도구 사용 경험"]), output)
    assert ok is False
    assert "데이터 시각화" in note


def test_clean_qualifications_pass():
    output = {"qualifications": ["SQL 기초 문법을 아는 사람"]}
    assert graders.grade_preferred(item(["데이터 시각화 도구 사용 경험"]), output)[0] is True


def test_not_applicable_without_preferred():
    output = {"qualifications": ["SQL 기초 문법을 아는 사람"]}
    assert graders.grade_preferred(item([]), output)[0] is None


def test_registered_in_summary_graders():
    assert "preferred" in graders.SUMMARY_GRADERS
