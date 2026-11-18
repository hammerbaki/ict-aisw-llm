"""스터디룸 예약: 8장의 예제 웹앱(키트 제공). 파이썬 표준 라이브러리만 쓴다.

실행
    python server.py            http://localhost:8200/ 에서 연다
    python server.py 8201       포트를 바꿀 때 (8200을 이미 쓰고 있으면)

끝점
    GET    /api/rooms                         방의 목록
    GET    /api/reservations?date=YYYY-MM-DD  그날의 예약 목록
    POST   /api/reservations                  예약을 만든다 (JSON 본문)
    DELETE /api/reservations/{id}             예약을 지운다

자료는 메모리에 둔다. 서버를 끄면 예약이 모두 사라진다.
이 파일은 8장에서 분석할 대상이다. 8장의 실습은 이 파일을 읽기 전에
브라우저의 네트워크 기록(HAR)으로 서버의 동작을 먼저 알아낸다.
"""
import json
import re
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

STATIC = Path(__file__).resolve().parent / "static"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8"}
TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

ROOMS = [
    {"id": 1, "name": "스터디룸 A", "capacity": 4},
    {"id": 2, "name": "스터디룸 B", "capacity": 8},
]
RESERVATIONS = []
NEXT_ID = [1]


class Invalid(Exception):
    """요청의 내용이 틀렸다(422)."""


def parse_date(text):
    try:
        return date.fromisoformat(text).isoformat()
    except (TypeError, ValueError):
        raise Invalid("date는 2027-05-17처럼 YYYY-MM-DD 꼴이어야 한다")


def parse_time(text, field):
    if not isinstance(text, str) or not TIME.match(text):
        raise Invalid(f"{field}는 10:00처럼 HH:MM 꼴이어야 한다")
    return text


def validate(body):
    """요청 하나만 보고 판정한다: 형식, 필수, 범위."""
    if not isinstance(body, dict):
        raise Invalid("본문은 JSON 객체여야 한다")
    room_id = body.get("room_id")
    if not isinstance(room_id, int) or isinstance(room_id, bool):
        raise Invalid("room_id는 정수여야 한다")
    day = parse_date(body.get("date"))
    start = parse_time(body.get("start"), "start")
    end = parse_time(body.get("end"), "end")
    if end <= start:
        raise Invalid("끝 시각은 시작 시각보다 뒤여야 한다")
    name = body.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 20:
        raise Invalid("name은 1~20자여야 한다")
    return {"room_id": room_id, "date": day, "start": start, "end": end, "name": name.strip()}


class Handler(BaseHTTPRequestHandler):
    server_version = "StudyRoomDemo/1.0"
    protocol_version = "HTTP/1.1"

    def send_json(self, status, data=None):
        raw = b"" if data is None else json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        if data is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        if status != 204:  # 204에는 Content-Length를 보내지 않는다(RFC 9110 8.6)
            self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/api/rooms":
            return self.send_json(200, ROOMS)
        if url.path == "/api/reservations":
            try:
                day = parse_date(parse_qs(url.query).get("date", [None])[0])
            except Invalid as e:
                return self.send_json(422, {"detail": str(e)})
            return self.send_json(200, [r for r in RESERVATIONS if r["date"] == day])
        name = "index.html" if url.path == "/" else url.path.lstrip("/")
        file = STATIC / name
        if "/" in name or not file.is_file() or file.suffix not in TYPES:
            return self.send_json(404, {"detail": "없는 주소이다"})
        raw = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPES[file.suffix])
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if urlsplit(self.path).path != "/api/reservations":
            return self.send_json(404, {"detail": "없는 주소이다"})
        try:
            body = validate(json.loads(raw or b"null"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(422, {"detail": "본문이 UTF-8의 JSON이 아니다"})
        except Invalid as e:
            return self.send_json(422, {"detail": str(e)})
        if not any(room["id"] == body["room_id"] for room in ROOMS):
            return self.send_json(404, {"detail": "없는 방이다"})
        for r in RESERVATIONS:
            same = r["room_id"] == body["room_id"] and r["date"] == body["date"]
            if same and body["start"] < r["end"] and r["start"] < body["end"]:
                return self.send_json(409, {"detail": "겹치는 예약이 있다"})
        new = {"id": NEXT_ID[0], **body}
        NEXT_ID[0] += 1
        RESERVATIONS.append(new)
        return self.send_json(201, new)

    def do_DELETE(self):
        m = re.fullmatch(r"/api/reservations/(\d+)", urlsplit(self.path).path)
        if not m:
            return self.send_json(404, {"detail": "없는 주소이다"})
        for r in RESERVATIONS:
            if r["id"] == int(m.group(1)):
                RESERVATIONS.remove(r)
                return self.send_json(204)
        return self.send_json(404, {"detail": "없는 예약이다"})


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # Windows의 Git Bash에서도 한글이 깨지지 않게
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8200
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"스터디룸 예약 예제 웹앱: http://localhost:{port}/  (끝내려면 Ctrl+C)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
