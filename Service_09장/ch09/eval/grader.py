"""규칙 기반 채점기. 응답 한 건을 다섯 항목으로 판정한다. 사람의 인상이 아니라 정해 둔 규칙으로만 채점한다.

항목
  json   응답 전체가 JSON 객체인가(앞뒤 설명 문장, 코드 울타리가 있으면 실패)
  형식   네 필드가 정해진 이름과 타입으로 있는가(api/schema.py의 Summary로 검사)
  마감일 정답 마감일과 같은가(정답이 null이면 null이어야 한다)
  자격   자격요건에 꼭 들어갈 말이 모두 있고, 우대 사항의 말은 없는가
  근거   공고에 없는 말(금지어)이 응답 어디에도 없는가

json이 실패하면 나머지 네 항목도 실패로 센다. 프로그램이 읽지 못하는 답은 쓸 수 없기 때문이다.
"""
from __future__ import annotations

import json

from api.schema import parse_summary

GRADER_VERSION = "1.0"
CHECKS = ("json", "형식", "마감일", "자격", "근거")


def grade(response: str, answer: dict) -> dict:
    result = {name: False for name in CHECKS}
    try:
        data = json.loads(response.strip())
    except (json.JSONDecodeError, AttributeError):
        result["사유"] = "JSON 아님"
        return result
    if not isinstance(data, dict):
        result["사유"] = "JSON 객체 아님"
        return result
    result["json"] = True

    summary, reason = parse_summary(response)
    result["형식"] = summary is not None
    reasons = [] if summary else [reason]

    result["마감일"] = data.get("마감일", "없음") == answer["마감일"]
    if not result["마감일"]:
        reasons.append(f"마감일 {data.get('마감일', '(필드 없음)')!r} ≠ 정답 {answer['마감일']!r}")

    quals = data.get("자격요건")
    qual_text = " ".join(quals) if isinstance(quals, list) else ""
    missing = [w for w in answer["자격요건_포함"] if w not in qual_text]
    mixed = [w for w in answer["자격요건_제외"] if w in qual_text]
    result["자격"] = isinstance(quals, list) and not missing and not mixed
    if missing:
        reasons.append(f"자격요건에 없음: {missing}")
    if mixed:
        reasons.append(f"우대 사항이 섞임: {mixed}")

    whole = json.dumps(data, ensure_ascii=False)
    invented = [w for w in answer["금지어"] if w in whole]
    result["근거"] = not invented
    if invented:
        reasons.append(f"공고에 없는 말: {invented}")

    result["사유"] = "; ".join(r for r in reasons if r)
    return result


def score(result: dict) -> int:
    return sum(1 for name in CHECKS if result[name])
