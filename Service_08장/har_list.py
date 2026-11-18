"""HAR 파일의 /api/ 요청을 (메서드, 경로, 상태 코드)로 묶어 센다. 표준 라이브러리만 쓴다."""
import collections
import json
import sys
from urllib.parse import urlsplit

sys.stdout.reconfigure(encoding="utf-8")  # Windows의 Git Bash에서도 한글이 깨지지 않게
with open(sys.argv[1], encoding="utf-8") as f:
    har = json.load(f)
count = collections.Counter()
for i, e in enumerate(har["log"]["entries"]):
    u = urlsplit(e["request"]["url"])
    if not u.path.startswith("/api/"):
        continue
    count[(e["request"]["method"], u.path, e["response"]["status"])] += 1
    print(f'{i:>3} {e["request"]["method"]:<6} {u.path}{"?" + u.query if u.query else ""} -> {e["response"]["status"]}')
print("--- 묶음")
for (m, p, s), n in sorted(count.items(), key=lambda x: (x[0][1], x[0][0], x[0][2])):
    print(f"{m:<6} {p:<28} {s}  {n}회")
