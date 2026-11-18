from fastapi.testclient import TestClient

import app as m

client = TestClient(m.app)
BODY = {"room_id": 1, "date": "2027-05-17", "start": "10:00", "end": "11:00", "name": "연습"}

def setup_function():
    m.RESERVATIONS.clear()
    m.NEXT_ID["value"] = 1

def test_create_and_list():
    assert client.post("/api/reservations", json=BODY).status_code == 201
    got = client.get("/api/reservations", params={"date": "2027-05-17"}).json()
    assert len(got) == 1 and got[0]["name"] == "연습"

def test_overlap_is_rejected():
    client.post("/api/reservations", json=BODY)
    r = client.post("/api/reservations", json={**BODY, "start": "10:30", "end": "11:30"})
    assert r.status_code == 409

def test_touching_is_allowed():
    client.post("/api/reservations", json=BODY)
    r = client.post("/api/reservations", json={**BODY, "start": "11:00", "end": "12:00"})
    assert r.status_code == 201

def test_end_before_start():
    r = client.post("/api/reservations", json={**BODY, "start": "11:00", "end": "10:00"})
    assert r.status_code == 422

def test_delete_twice():
    client.post("/api/reservations", json=BODY)
    assert client.delete("/api/reservations/1").status_code == 204
    assert client.delete("/api/reservations/1").status_code == 404
