/* SCR-03·04 지원 일정과 지원 일정 등록: 추가, 날짜 순 표시, 입력 오류, 삭제 확인, 저장 실패 (REQ-009, REQ-010, REQ-026, REQ-031, REQ-032, REQ-039) */
let jobsById = new Map();

function getSchedule() {
  return readList(STORAGE_KEYS.schedule);
}

function makeItem(entry) {
  const job = jobsById.get(entry.jobId);
  const item = el("li", "schedule-item");
  item.dataset.date = entry.date;
  item.dataset.id = entry.id;
  item.append(el("span", "schedule-date", entry.date));
  item.append(el("span", "schedule-stage", entry.stage));
  item.append(el("span", "schedule-job", job ? `${job.company} · ${job.title}` : "삭제된 공고"));
  if (entry.memo) item.append(el("span", "schedule-memo", entry.memo));
  const remove = el("button", "delete-schedule", "삭제");
  remove.type = "button";
  remove.setAttribute("aria-label", `${entry.date} ${entry.stage} 일정 삭제`);
  remove.addEventListener("click", () => {
    // REQ-032: 지우기 전에 확인을 받는다
    if (!confirm(`${entry.date} ${entry.stage} 일정을 삭제할까요? 삭제하면 되돌릴 수 없습니다.`)) return;
    writeList(STORAGE_KEYS.schedule, getSchedule().filter((x) => x.id !== entry.id));
    render();
  });
  item.append(remove);
  return item;
}

function render() {
  const entries = getSchedule().sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
  document.getElementById("schedule-list").replaceChildren(...entries.map(makeItem));
  document.getElementById("schedule-empty").hidden = entries.length > 0;
}

function showError(message) {
  const box = document.getElementById("schedule-error");
  box.textContent = message;
  box.hidden = !message;
}

function onSubmit(event) {
  event.preventDefault();
  const jobId = document.getElementById("schedule-job").value;
  const stage = document.getElementById("schedule-stage").value;
  const date = document.getElementById("schedule-date").value;
  const memo = document.getElementById("schedule-memo").value.trim().slice(0, 100);
  if (!jobId || !date) {
    showError("공고와 날짜를 모두 입력해야 일정을 추가할 수 있습니다.");
    return;
  }
  const entry = { id: `S-${Date.now()}-${Math.floor(Math.random() * 1000)}`, jobId, stage, date, memo };
  if (!writeList(STORAGE_KEYS.schedule, getSchedule().concat(entry))) {
    showError("브라우저 저장소에 쓰지 못했습니다. 사생활 보호 모드나 저장 공간을 확인하십시오.");
    return;
  }
  showError("");
  document.getElementById("schedule-date").value = "";
  document.getElementById("schedule-memo").value = "";
  render();
}

async function start() {
  try {
    const jobs = await loadJobs();
    jobsById = new Map(jobs.map((job) => [job.id, job]));
  } catch (error) {
    jobsById = new Map();
  }
  const select = document.getElementById("schedule-job");
  for (const job of [...jobsById.values()].sort(compareByDeadline)) {
    const option = el("option", "", `${job.company} · ${job.title}`);
    option.value = job.id;
    select.append(option);
  }
  const preset = new URLSearchParams(location.search).get("job");
  if (preset && jobsById.has(preset)) select.value = preset;
  document.getElementById("schedule-form").addEventListener("submit", onSubmit);
  render();
}

start();
