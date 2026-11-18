"""스터디룸 예약 API. 자료는 메모리에 둔다(서버를 끄면 사라진다)."""
from datetime import date, time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="예약 API")

ROOMS = [
    {"id": 1, "name": "스터디룸 A", "capacity": 4},
    {"id": 2, "name": "스터디룸 B", "capacity": 8},
]
RESERVATIONS: list[dict] = []
NEXT_ID = {"value": 1}

class ReservationIn(BaseModel):
    room_id: int
    date: date
    start: time
    end: time
    name: str = Field(min_length=1, max_length=20)

@app.get("/api/rooms")
def list_rooms():
    return ROOMS

@app.get("/api/reservations")
def list_reservations(date: date):
    return [r for r in RESERVATIONS if r["date"] == date]

@app.post("/api/reservations", status_code=201)
def create_reservation(body: ReservationIn):
    if not any(room["id"] == body.room_id for room in ROOMS):
        raise HTTPException(status_code=404, detail="없는 방이다")
    if body.end <= body.start:
        raise HTTPException(status_code=422, detail="끝 시각은 시작 시각보다 뒤여야 한다")
    for r in RESERVATIONS:
        same = r["room_id"] == body.room_id and r["date"] == body.date
        if same and body.start < r["end"] and r["start"] < body.end:
            raise HTTPException(status_code=409, detail="겹치는 예약이 있다")
    new = {"id": NEXT_ID["value"], **body.model_dump()}
    NEXT_ID["value"] += 1
    RESERVATIONS.append(new)
    return new

@app.delete("/api/reservations/{reservation_id}", status_code=204)
def delete_reservation(reservation_id: int):
    for r in RESERVATIONS:
        if r["id"] == reservation_id:
            RESERVATIONS.remove(r)
            return
    raise HTTPException(status_code=404, detail="없는 예약이다")
