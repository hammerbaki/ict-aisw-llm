"""고용24 채용정보 목록 응답(XML)을 화면용 JSON으로 바꾼다. (「LLM 서비스 개발」 5장 키트)

쓰는 법: python xml2json.py 응답.xml jobs.json

KEEP에 적은 항목만 남긴다. 받은 시각(fetched)은 응답 파일의 수정 시각이다.
응답의 바깥 구조는 가정하지 않고, wantedAuthNo를 자식으로 가진 요소를 공고 한 건으로 본다.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# 화면에 쓰는 항목만 남긴다. 자료 항목표의 「내 서비스에서」 칸을 따른다.
KEEP = ["wantedAuthNo", "company", "title", "salTpNm", "sal", "region",
        "career", "minEdubg", "regDt", "closeDt", "wantedInfoUrl"]


def main(src, dst):
    root = ET.parse(src).getroot()
    jobs = []
    for el in root.iter():
        # 공고 한 건: wantedAuthNo를 자식으로 가진 요소
        if el.find("wantedAuthNo") is None:
            continue
        job = {k: (el.findtext(k) or "").strip() for k in KEEP}
        jobs.append(job)
    out = {
        "source": "고용24 OPEN-API 채용정보",
        "fetched": datetime.fromtimestamp(os.path.getmtime(src)).strftime("%Y-%m-%d %H:%M"),
        "count": len(jobs),
        "jobs": jobs,
    }
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    empty = {k: sum(1 for j in jobs if not j[k]) for k in KEEP}
    print(f"공고 {len(jobs)}건 → {dst}")
    print("빈 값:", {k: v for k, v in empty.items() if v} or "없음")
    print("날짜가 아닌 closeDt:", sorted({j["closeDt"] for j in jobs if not j["closeDt"][:2].isdigit()}) or "없음")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
