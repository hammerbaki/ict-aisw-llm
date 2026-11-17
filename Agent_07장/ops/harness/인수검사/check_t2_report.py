"""작업 카드 T2(2027-09-11 질의응답 장애 보고서)의 보고서 검사.

사용: python check_t2_report.py <실험 저장소 폴더>
결과: 항목별 통과 여부를 JSON으로 출력한다. 통과 수가 인수 검사 점수이다.

기준이 된 사실(logs/의 가상 기록에서 확인한 것)
- 2027-09-11 16:05:08, 16:06:02, 16:08:00에 POST /api/ask가 503으로 실패(AuthenticationError) 3건
- 그 뒤 질의응답의 첫 성공은 19:03:04(llm.log task=ask). 16:17의 성공은 요약(summary) 기능이다
- 기록에는 인증 실패의 원인(키 만료, 교체 등)이 없다. 원인은 추정으로 표시되어야 한다
"""
import json
import re
import sys
from pathlib import Path

REPORT = Path("docs/운영/장애보고/2027-09-11.md")  # 4장 스킬의 저장 위치 규칙(docs/운영/장애보고/YYYY-MM-DD.md)
# 절 이름: 4장 보고서 서식의 여섯 절. 같은 뜻의 다른 이름도 받는다
SECTIONS = [("요약",), ("영향",), ("경과", "타임라인"), ("원인",), ("조치", "대책"), ("근거",)]


def section(text, name):
    """'## 이름'으로 시작하는 절의 본문을 돌려준다. 없으면 빈 문자열."""
    found = re.search(rf"^##\s*[^\n]*{name}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return found.group(1) if found else ""


def check(repo):
    path = Path(repo) / REPORT
    if not path.exists():
        return {"exists": False, "passed": 0, "total": 10, "items": {}}
    text = path.read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    cause = section(text, "원인")
    items = {
        "절 6개(요약·영향·경과·원인·조치·근거)": all(any(n in h for h in headings for n in names) for names in SECTIONS),
        "날짜 2027-09-11": "2027-09-11" in text,
        "경로 /api/ask": "/api/ask" in text,
        "오류 AuthenticationError": "AuthenticationError" in text,
        "실패 3건": bool(re.search(r"(3\s*(건|회|번|개)|세\s*건)", text)),
        "첫 실패 16:05": "16:05" in text,
        "마지막 실패 16:08": "16:08" in text,
        "질의응답 첫 성공 19:03": "19:03" in text,
        "원인에 추정 표시": bool(re.search(r"추정|확인 필요|확인되지 않", cause)),
        "기록 파일 근거 2종 이상": sum(name in text for name in ("error.log", "access.log", "llm.log")) >= 2,
    }
    passed = sum(items.values())
    return {"exists": True, "passed": passed, "total": len(items), "items": items}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(check(sys.argv[1]), ensure_ascii=False, indent=2))
