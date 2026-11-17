/* SCR-07 관심 공고: 저장한 공고 목록(마감일 순), 해제, 빈 상태, 마감 표시 (REQ-008, REQ-009, REQ-038, REQ-040, REQ-003) */
let jobsById = new Map();

function makeSavedItem(job, today) {
  const item = el("li", "job-card saved-item");
  item.dataset.jobId = job.id;
  const link = el("a", "job-link");
  link.href = withToday(`detail.html?id=${encodeURIComponent(job.id)}`);
  link.append(el("span", "job-title", job.title));
  item.append(link);
  item.append(el("p", "job-company", job.company));
  const meta = el("p", "job-meta");
  meta.append(el("span", "job-deadline", formatDeadline(job.deadline)));
  const badge = makeDeadlineBadge(job.deadline, today);
  if (badge) meta.append(badge);
  item.append(meta);
  const remove = el("button", "remove-saved", "관심 해제");
  remove.type = "button";
  remove.setAttribute("aria-label", `${job.title} 관심 해제`);
  remove.addEventListener("click", () => {
    toggleSaved(job.id);
    render();
  });
  item.append(remove);
  return item;
}

function render() {
  const today = getToday();
  // 자료에 없는 번호(자료가 바뀌어 사라진 공고)는 보이지 않는다.
  const jobs = getSavedIds().map((id) => jobsById.get(id)).filter(Boolean).sort(compareByDeadline);
  document.getElementById("saved-list").replaceChildren(...jobs.map((job) => makeSavedItem(job, today)));
  document.getElementById("saved-count").textContent = `관심 공고 ${jobs.length}건`;
  document.getElementById("saved-empty").hidden = jobs.length > 0;
}

async function start() {
  try {
    const jobs = await loadJobs();
    jobsById = new Map(jobs.map((job) => [job.id, job]));
  } catch (error) {
    jobsById = new Map();
  }
  render();
}

start();
