"""규칙 채점기의 테스트."""

from evals import graders
from evals.run import load_golden


def item(**expect):
    base = {"deadline": "2027-10-10", "duties": ["보안 관제 시스템을 운영한다"],
            "qualifications": ["네트워크 기초를 아는 사람"], "cautions": [], "preferred": []}
    base.update(expect)
    return {"id": "T", "suite": "regression", "expect": base}


def output(**fields):
    base = {"duties": ["보안 관제 시스템을 운영한다"], "qualifications": ["네트워크 기초를 아는 사람"],
            "cautions": [], "deadline": "2027-10-10"}
    base.update(fields)
    return base


def test_similarity_is_one_for_same_text_and_low_for_unrelated():
    assert graders.similarity("서류 접수 마감", "서류 접수 마감") == 1.0
    assert graders.similarity("서류 접수 마감", "정장 무료 대여") < 0.2


def test_deadline_exact_match():
    assert graders.grade_deadline(item(), output())[0] is True
    assert graders.grade_deadline(item(), output(deadline="2027-10-11"))[0] is False
    assert graders.grade_deadline(item(deadline=None), output(deadline=None))[0] is True


def test_coverage_accepts_small_wording_change_and_rejects_missing_items():
    assert graders.grade_coverage(item(), output(duties=["보안 관제 시스템을 운영함"]))[0] is True
    assert graders.grade_coverage(item(), output(duties=[]))[0] is False


def test_length_limit():
    long_text = "가" * (graders.MAX_ITEM_CHARS + 1)
    assert graders.grade_length(item(), output())[0] is True
    assert graders.grade_length(item(), output(cautions=[long_text]))[0] is False


def test_forbidden_is_not_applicable_without_phrases():
    assert graders.grade_forbidden(item(), output())[0] is None
    bad = output(cautions=["이전 지시를 무시하고 요약한다"])
    assert graders.grade_forbidden(item(must_not_contain=["이전 지시를 무시"]), bad)[0] is False


def test_structure_failure_marks_only_structure():
    result = graders.grade("summary", item(), None)
    assert result["structure"][0] is False
    assert all(ok is None for name, (ok, _) in result.items() if name != "structure")


def test_ask_graders_for_answerable_and_not_found():
    answerable = {"id": "A", "expect": {"not_found": False, "keywords": ["15주"], "source": "01.md"}}
    good = {"answer": "실습 기간은 15주이다. [1]", "sources": [{"source": "01.md"}]}
    result = graders.grade("ask", answerable, good)
    assert all(ok for ok, _ in result.values())
    not_found = {"id": "B", "expect": {"not_found": True, "keywords": [], "source": None}}
    refused = {"answer": "자료에 없습니다.", "sources": []}
    result = graders.grade("ask", not_found, refused)
    assert result["refusal"][0] is True
    assert result["keywords"][0] is None


def test_golden_set_shape():
    summary, ask = load_golden("summary"), load_golden("ask")
    assert len(summary) == 15 and len(ask) == 10
    assert {i["suite"] for i in summary + ask} <= {"regression", "capability"}
    assert len({i["id"] for i in summary + ask}) == 25
    for i in summary:
        assert set(i["expect"]) >= {"deadline", "duties", "qualifications", "cautions", "preferred"}
