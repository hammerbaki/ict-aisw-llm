"""고용24 채용정보를 서버에서 불러 화면에 넘기는 끝점.

인증키는 환경 변수 WORK24_KEY에서 읽는다. 브라우저에는 가지 않는다.
"""
import os
import time
import xml.etree.ElementTree as ET

import httpx
from fastapi import FastAPI, HTTPException

URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do"
KEEP = ["wantedAuthNo", "company", "title", "region", "career", "closeDt", "wantedInfoUrl"]
TTL = 600  # 초. 같은 자료를 10분 동안 다시 부르지 않는다

app = FastAPI()
client = httpx.Client(timeout=5.0)
_cache = {"at": 0.0, "jobs": None}


def parse(xml_text):
    root = ET.fromstring(xml_text)
    return [{k: (el.findtext(k) or "").strip() for k in KEEP}
            for el in root.iter() if el.find("wantedAuthNo") is not None]


@app.get("/api/jobs")
def jobs():
    key = os.environ.get("WORK24_KEY")
    if not key:
        raise HTTPException(503, "서버에 인증키가 설정되지 않았다")
    now = time.time()
    if _cache["jobs"] is not None and now - _cache["at"] < TTL:
        return {"cached": True, "count": len(_cache["jobs"]), "jobs": _cache["jobs"]}
    try:
        r = client.get(URL, params={"authKey": key, "callTp": "L", "returnType": "XML",
                                    "startPage": 1, "display": 10})
        r.raise_for_status()
        found = parse(r.text)
    except (httpx.HTTPError, ET.ParseError):
        raise HTTPException(502, "공고 자료를 받지 못했다")
    _cache.update(at=now, jobs=found)
    return {"cached": False, "count": len(found), "jobs": found}
