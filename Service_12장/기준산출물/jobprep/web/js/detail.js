/* SCR-02 공고 상세: 항목 표시, 관심 공고 저장·해제, 없는 공고 안내, 마감 표시 (REQ-030, REQ-008, REQ-038, REQ-009, REQ-037, REQ-003) */
function fillList(id, items) {
  document.getElementById(id).replaceChildren(...items.map((text) => el("li", "", text)));
}

function updateSaveButton(button, saved) {
  button.textContent = saved ? "관심 해제" : "관심 공고 저장";
  button.setAttribute("aria-pressed", String(saved));
}

function showJob(job) {
  const today = getToday();
  document.title = `${job.title} | 취업 준비 지원`;
  document.getElementById("job-title").textContent = job.title;
  document.getElementById("job-company").textContent = job.company;
  document.getElementById("job-category").textContent = job.category;
  document.getElementById("job-region").textContent = job.region;
  document.getElementById("job-employment").textContent = job.employment_type;
  document.getElementById("job-career").textContent = job.career;
  document.getElementById("job-education").textContent = job.education;
  document.getElementById("job-deadline").textContent = job.deadline || "상시 채용";
  document.getElementById("job-summary").textContent = job.summary;
  fillList("job-requirements", job.requirements);
  fillList("job-preferred", job.preferred);
  const badge = makeDeadlineBadge(job.deadline, today);
  if (badge) document.getElementById("job-badges").append(badge);

  const button = document.getElementById("save-toggle");
  updateSaveButton(button, isSaved(job.id));
  button.addEventListener("click", () => {
    const saved = toggleSaved(job.id);
    updateSaveButton(button, saved);
    document.getElementById("save-message").textContent = saved
      ? "관심 공고에 저장했습니다."
      : "관심 공고에서 뺐습니다.";
  });
  document.getElementById("add-schedule").href = withToday(`schedule.html?job=${encodeURIComponent(job.id)}`);
  document.getElementById("job-detail").hidden = false;
}

async function start() {
  const id = new URLSearchParams(location.search).get("id");
  let jobs = [];
  try {
    jobs = await loadJobs();
  } catch (error) {
    jobs = [];
  }
  const job = jobs.find((item) => item.id === id);
  if (job) {
    showJob(job);
  } else {
    document.getElementById("not-found").hidden = false;
  }
}

start();
