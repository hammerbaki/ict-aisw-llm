"""예제 웹앱의 끝점이 견본 서버와 같은 상태 코드를 내는지 확인한다(키트를 고친 뒤 깨지지 않게)."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import server

BODY = {"room_id": 1, "date": "2027-05-17", "start": "10:00", "end": "11:00", "name": "연습"}


@pytest.fixture
def base():
    server.RESERVATIONS.clear()
    server.NEXT_ID[0] = 1
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def call(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req) as res:
            raw = res.read()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"null")


def test_rooms_and_page(base):
    assert call(base, "GET", "/api/rooms")[0] == 200
    with urllib.request.urlopen(base + "/") as res:
        assert "스터디룸 예약" in res.read().decode("utf-8")


def test_create_keeps_hh_mm(base):
    status, body = call(base, "POST", "/api/reservations", BODY)
    assert status == 201 and body["start"] == "10:00"


def test_overlap_409_touching_201(base):
    call(base, "POST", "/api/reservations", BODY)
    assert call(base, "POST", "/api/reservations", {**BODY, "start": "10:30", "end": "11:30"})[0] == 409
    assert call(base, "POST", "/api/reservations", {**BODY, "start": "11:00", "end": "12:00"})[0] == 201


def test_invalid_422_and_unknown_room_404(base):
    assert call(base, "POST", "/api/reservations", {**BODY, "start": "11:00", "end": "10:00"})[0] == 422
    assert call(base, "POST", "/api/reservations", {**BODY, "name": ""})[0] == 422
    assert call(base, "POST", "/api/reservations", {**BODY, "room_id": 9})[0] == 404
    assert call(base, "GET", "/api/reservations?date=5-17")[0] == 422


def test_delete_twice(base):
    call(base, "POST", "/api/reservations", BODY)
    assert call(base, "DELETE", "/api/reservations/1")[0] == 204
    assert call(base, "DELETE", "/api/reservations/1")[0] == 404
