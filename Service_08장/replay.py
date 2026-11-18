"""HAR에 기록된 /api/ 요청을 내 서버에 같은 순서로 보내고 상태 코드를 견준다."""
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

sys.stdout.reconfigure(encoding="utf-8")  # Windows의 Git Bash에서도 한글이 깨지지 않게
har, base = sys.argv[1], sys.argv[2].rstrip("/")
with open(har, encoding="utf-8") as f:
    entries = json.load(f)["log"]["entries"]
same = diff = 0
for i, e in enumerate(entries):
    req = e["request"]
    u = urlsplit(req["url"])
    if not u.path.startswith("/api/"):
        continue
    data = req.get("postData", {}).get("text")
    r = urllib.request.Request(
        base + u.path + ("?" + u.query if u.query else ""),
        data=data.encode("utf-8") if data else None,
        method=req["method"],
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        got = urllib.request.urlopen(r).status
    except urllib.error.HTTPError as err:
        got = err.code
    want = e["response"]["status"]
    mark = "같다" if got == want else "다르다"
    same, diff = same + (got == want), diff + (got != want)
    print(f'{i:>3} {mark} | 기록 {want}, 내 서버 {got} | {req["method"]} {u.path}')
print(f"같다 {same}건, 다르다 {diff}건")
