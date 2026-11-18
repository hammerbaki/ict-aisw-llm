"""모의 모드(LLM_FAKE=1)의 요약기. 모델을 흉내 내지 않고, 공고의 [제목] 칸을 규칙으로 옮겨 적는다.

목적은 하나다. 키가 없거나 한도에 닿아도 API와 웹을 끝까지 돌려 보는 것.
그러므로 이 결과는 요약 품질의 근거가 아니다. 품질은 실제 호출과 평가 문항으로 잰다.
"""
from __future__ import annotations

import re

SECTION = re.compile(r"^\[(?P<name>[^\]]+)\]\s*(?P<rest>.*)$")
DATE = re.compile(r"(?P<y>\d{4})\s*(?:[-./]|년)\s*(?P<m>\d{1,2})\s*(?:[-./]|월)\s*(?P<d>\d{1,2})")


def sections(text: str) -> dict[str, list[str]]:
    """'[주요 업무]' 같은 머리 줄 아래의 '- ' 항목을 모은다."""
    result: dict[str, list[str]] = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        m = SECTION.match(line)
        if m:
            current = m.group("name").replace(" ", "")
            result.setdefault(current, [])
            if m.group("rest"):
                result[current].append(m.group("rest").strip())
            continue
        if current and line.startswith("-"):
            result[current].append(line.lstrip("- ").strip())
    return result


def deadline(lines: list[str]) -> str | None:
    """접수 기간 칸에서 마지막 날짜를 마감일로 본다. 상시 채용이면 None."""
    joined = " ".join(lines)
    if "상시" in joined:
        return None
    found = list(DATE.finditer(joined))
    if not found:
        return None
    last = found[-1]
    return f"{int(last['y']):04d}-{int(last['m']):02d}-{int(last['d']):02d}"


def fake_summary(text: str) -> dict:
    s = sections(text)
    return {
        "핵심업무": (s.get("주요업무") or ["(모의) 공고에서 주요 업무 칸을 찾지 못함"])[:5],
        "자격요건": s.get("자격요건", [])[:8],
        "마감일": deadline(s.get("접수기간", [])),
        "주의점": s.get("유의사항", [])[:5],
    }
