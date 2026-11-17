"""규칙 채점기: 골든 세트의 기대값과 실제 출력을 비교해 기준별로 통과와 실패를 정한다.

채점기 하나는 (통과 여부, 설명)을 돌려주는 함수이다. 통과 여부가 None이면 그 문항에는
해당하지 않는 기준이라는 뜻이며, 통과율을 셀 때 빼고 센다.

요약(summary) 채점기
- structure: 요약을 JSON 구조로 읽었는가(SummaryError가 나지 않았는가)
- deadline: 마감일이 기대값과 정확히 같은가(정확 일치)
- coverage: 기대 항목(참조 답)을 출력이 얼마나 덮는가(참조 기반, 재현율 0.8 이상)
- length: 모든 항목이 50자 이내인가(규칙)
- forbidden: 출력에 들어가면 안 되는 문구가 없는가(규칙)

질의응답(ask) 채점기
- refusal: 답할 수 없는 질문에는 "자료에 없습니다."로, 답할 수 있는 질문에는 그 밖의 답으로 답했는가(정확 일치)
- keywords: 답에 기대 핵심어가 모두 들어 있는가(문자열 포함)
- citation: 답에 근거 번호가 있고 출처 목록이 비어 있지 않은가(구조)
- source: 기대한 자료 파일을 출처로 들었는가(정확 일치)
"""

from api.ask import NOT_FOUND

MAX_ITEM_CHARS = 50     # 요약 항목 하나의 최대 글자 수
COVERAGE_MIN = 0.8      # 참조 항목 가운데 출력이 덮어야 하는 비율
MATCH_MIN = 0.5         # 두 문장을 같은 항목으로 볼 최소 유사도
LIST_KEYS = ("duties", "qualifications", "cautions")


# ---------------------------------------------------------------------------
# 문장 유사도: 글자 두 개씩 묶은 조각(bigram)의 겹침으로 잰다. 형태소 분석기 없이 돈다.
# ---------------------------------------------------------------------------

def bigrams(text):
    """빈칸과 문장 부호를 뺀 글을 두 글자씩 잘라 집합으로 돌려준다."""
    chars = [ch for ch in text if ch.isalnum()]
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def similarity(a, b):
    """두 글의 bigram Dice 계수(0~1). 같은 글이면 1이다."""
    x, y = bigrams(a), bigrams(b)
    if not x or not y:
        return 0.0
    return 2 * len(x & y) / (len(x) + len(y))


def best_match(text, candidates):
    """candidates 가운데 text와 가장 비슷한 것의 유사도를 돌려준다."""
    return max((similarity(text, c) for c in candidates), default=0.0)


# ---------------------------------------------------------------------------
# 요약 채점기
# ---------------------------------------------------------------------------

def summary_items(output):
    """요약 출력의 세 목록을 한 목록으로 이어 돌려준다."""
    return [item for key in LIST_KEYS for item in output.get(key, [])]


def grade_structure(item, output):
    if output is None:
        return False, "요약을 JSON 구조로 읽지 못하였다"
    return True, ""


def grade_deadline(item, output):
    expected = item["expect"]["deadline"]
    actual = output.get("deadline")
    if actual == expected:
        return True, ""
    return False, f"마감일 기대 {expected}, 출력 {actual}"


def grade_coverage(item, output):
    refs = [ref for key in LIST_KEYS for ref in item["expect"][key]]
    if not refs:
        return None, "참조 항목 없음"
    produced = summary_items(output)
    hit = [ref for ref in refs if best_match(ref, produced) >= MATCH_MIN]
    recall = len(hit) / len(refs)
    if recall >= COVERAGE_MIN:
        return True, f"재현율 {recall:.2f}"
    missing = [ref for ref in refs if ref not in hit]
    return False, f"재현율 {recall:.2f}, 빠진 항목 {missing[:2]}"


def grade_length(item, output):
    long_items = [text for text in summary_items(output) if len(text) > MAX_ITEM_CHARS]
    if long_items:
        return False, f"{MAX_ITEM_CHARS}자 초과 {len(long_items)}개: {long_items[0][:30]}…"
    return True, ""


def grade_forbidden(item, output):
    phrases = item["expect"].get("must_not_contain", [])
    if not phrases:
        return None, "금지 문구 없음"
    text = " ".join(summary_items(output))
    found = [p for p in phrases if p in text]
    if found:
        return False, f"금지 문구 포함: {found}"
    return True, ""


SUMMARY_GRADERS = {
    "structure": grade_structure,
    "deadline": grade_deadline,
    "coverage": grade_coverage,
    "length": grade_length,
    "forbidden": grade_forbidden,
}


# ---------------------------------------------------------------------------
# 질의응답 채점기
# ---------------------------------------------------------------------------

def grade_refusal(item, output):
    expect_not_found = item["expect"]["not_found"]
    refused = output["answer"].strip() == NOT_FOUND
    if refused == expect_not_found:
        return True, ""
    if expect_not_found:
        return False, "답할 수 없는 질문에 답하였다"
    return False, "답할 수 있는 질문을 거절하였다"


def grade_keywords(item, output):
    if item["expect"]["not_found"]:
        return None, "해당 없음"
    missing = [k for k in item["expect"]["keywords"] if k not in output["answer"]]
    if missing:
        return False, f"핵심어 없음: {missing}"
    return True, ""


def grade_citation(item, output):
    if item["expect"]["not_found"]:
        return None, "해당 없음"
    if "[" in output["answer"] and output["sources"]:
        return True, ""
    return False, "근거 번호 또는 출처가 없다"


def grade_source(item, output):
    if item["expect"]["not_found"]:
        return None, "해당 없음"
    names = [s["source"] for s in output["sources"]]
    if item["expect"]["source"] in names:
        return True, ""
    return False, f"출처 기대 {item['expect']['source']}, 출력 {names}"


ASK_GRADERS = {
    "refusal": grade_refusal,
    "keywords": grade_keywords,
    "citation": grade_citation,
    "source": grade_source,
}


def grade(suite, item, output):
    """문항 하나의 출력을 모든 채점기로 채점해 {기준: (통과, 설명)}을 돌려준다.

    요약의 output이 None이면(구조 실패) structure만 실패로 적고 나머지 기준은 채점하지 않는다.
    시행의 통과 여부는 structure 실패로 이미 실패가 된다.
    """
    graders = SUMMARY_GRADERS if suite == "summary" else ASK_GRADERS
    if suite == "summary" and output is None:
        result = {name: (None, "구조 실패로 채점하지 않음") for name in graders}
        result["structure"] = grade_structure(item, output)
        return result
    return {name: fn(item, output) for name, fn in graders.items()}
