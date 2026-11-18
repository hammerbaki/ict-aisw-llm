// 스터디룸 예약 화면. 서버의 /api/ 끝점만 부른다.
const $ = (id) => document.getElementById(id);
let rooms = [];

function times() {
  const out = [];
  for (let h = 9; h <= 21; h++) {
    for (const m of ["00", "30"]) {
      if (h === 21 && m === "30") continue;
      out.push(String(h).padStart(2, "0") + ":" + m);
    }
  }
  return out;
}

function fill(select, values, labels) {
  select.replaceChildren();
  values.forEach((v, i) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = labels ? labels[i] : v;
    select.append(o);
  });
}

function say(text, kind) {
  $("message").textContent = text;
  $("message").className = kind || "";
}

async function loadRooms() {
  const res = await fetch("/api/rooms");
  rooms = await res.json();
  fill($("room"), rooms.map((r) => r.id), rooms.map((r) => `${r.name} (${r.capacity}명)`));
}

async function loadReservations() {
  const res = await fetch("/api/reservations?date=" + encodeURIComponent($("date").value));
  if (!res.ok) {
    say("목록을 읽지 못했다. 날짜를 확인한다.", "error");
    return;
  }
  const list = await res.json();
  const body = $("rows");
  body.replaceChildren();
  $("empty").hidden = list.length > 0;
  for (const r of list) {
    const tr = document.createElement("tr");
    const room = rooms.find((x) => x.id === r.room_id);
    for (const text of [room ? room.name : r.room_id, `${r.start}~${r.end}`, r.name]) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.append(td);
    }
    const td = document.createElement("td");
    const b = document.createElement("button");
    b.textContent = "취소";
    b.addEventListener("click", () => cancel(r.id));
    td.append(b);
    tr.append(td);
    body.append(tr);
  }
}

async function reserve(event) {
  event.preventDefault();
  const start = $("start").value;
  const end = $("end").value;
  // 화면의 검사는 편의이다. 같은 규칙을 서버도 판정한다.
  if (end <= start) {
    say("끝 시각은 시작 시각보다 뒤여야 한다.", "error");
    return;
  }
  const res = await fetch("/api/reservations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      room_id: Number($("room").value),
      date: $("date").value,
      start,
      end,
      name: $("name").value,
    }),
  });
  if (res.status === 201) {
    say("예약하였다.", "ok");
  } else if (res.status === 409) {
    say("그 시간에는 이미 예약이 있다. 다른 시간을 고른다.", "error");
  } else {
    const data = await res.json().catch(() => ({}));
    say("예약하지 못했다: " + (data.detail || res.status), "error");
  }
  await loadReservations();
}

async function cancel(id) {
  const res = await fetch("/api/reservations/" + id, { method: "DELETE" });
  if (res.status === 204) {
    say("취소하였다.", "ok");
  } else if (res.status === 404) {
    say("이미 취소되었거나 없는 예약이다. 목록을 다시 읽었다.", "error");
  } else {
    say("취소하지 못했다: " + res.status, "error");
  }
  await loadReservations();
}

async function main() {
  const t = times();
  fill($("start"), t);
  fill($("end"), t);
  $("start").value = "10:00";
  $("end").value = "11:00";
  const d = new Date();
  $("date").value = [d.getFullYear(), String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0")].join("-");
  $("date").addEventListener("change", loadReservations);
  $("form").addEventListener("submit", reserve);
  await loadRooms();
  await loadReservations();
}

main();
