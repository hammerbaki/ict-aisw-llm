"""채점기는 정해 둔 규칙대로만 판정하는가."""
import json

from eval.grader import grade, score

ANSWER = {"id": "T", "마감일": "2027-06-14", "자격요건_포함": ["테스트"], "자격요건_제외": ["ISTQB"],
          "금지어": ["합격 보장"]}
GOOD = {"핵심업무": ["기능 시험"], "자격요건": ["소프트웨어 테스트 교육 이수"], "마감일": "2027-06-14", "주의점": []}


def j(d):
    return json.dumps(d, ensure_ascii=False)


def test_perfect():
    assert score(grade(j(GOOD), ANSWER)) == 5


def test_code_fence_fails_everything():
    r = grade("```json\n" + j(GOOD) + "\n```", ANSWER)
    assert score(r) == 0 and r["사유"] == "JSON 아님"


def test_prose_before_json_fails():
    assert grade("요약입니다.\n" + j(GOOD), ANSWER)["json"] is False


def test_wrong_deadline():
    r = grade(j({**GOOD, "마감일": "2027-06-21"}), ANSWER)
    assert r["마감일"] is False and r["형식"] is True and score(r) == 4


def test_null_deadline_must_be_null():
    ans = {**ANSWER, "마감일": None}
    assert grade(j({**GOOD, "마감일": None}), ans)["마감일"] is True
    assert grade(j({**GOOD, "마감일": "2027-12-31"}), ans)["마감일"] is False


def test_preferred_mixed_into_requirements():
    r = grade(j({**GOOD, "자격요건": GOOD["자격요건"] + ["ISTQB 보유"]}), ANSWER)
    assert r["자격"] is False


def test_invented_words():
    r = grade(j({**GOOD, "주의점": ["합격 보장"]}), ANSWER)
    assert r["근거"] is False


def test_wrong_keys_fail_format():
    r = grade(j({"deadline": "2027-06-14"}), ANSWER)
    assert r["json"] is True and r["형식"] is False and r["마감일"] is False


def test_bad_date_format_fails_format():
    r = grade(j({**GOOD, "마감일": "2027.06.14"}), {**ANSWER, "마감일": "2027.06.14"})
    assert r["형식"] is False
