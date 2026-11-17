// 공고 목록 화면: 목록을 불러와 그리고, 분야·검색어·관심 공고로 고른다.

const statusBox = document.getElementById("status");
const listBox = document.getElementById("job-list");
const fieldSelect = document.getElementById("field");
const keywordInput = document.getElementById("keyword");
const onlyFavorites = document.getElementById("only-favorites");

function renderJob(job) {
  const item = el("li", null, "job-card");

  const star = el("button", isFavorite(job.id) ? "★" : "☆", "star");
  star.type = "button";
  star.setAttribute("aria-pressed", String(isFavorite(job.id)));
  star.setAttribute("aria-label", `${job.title} 관심 공고 표시`);
  star.addEventListener("click", () => {
    const on = toggleFavorite(job.id);
    star.textContent = on ? "★" : "☆";
    star.setAttribute("aria-pressed", String(on));
    if (onlyFavorites.checked && !on) item.remove();
  });

  const link = el("a", job.title, "job-title");
  link.href = `job.html?id=${job.id}`;

  const meta = el("p", `${job.company} · ${job.field} · ${job.location} · ${job.employment_type}`, "job-meta");
  const deadline = el("p", `마감 ${job.deadline} (${dDay(job.days_left)})`, "job-deadline");

  item.append(star, link, meta, deadline);
  return item;
}

async function loadJobs() {
  const params = new URLSearchParams();
  if (fieldSelect.value) params.set("field", fieldSelect.value);
  if (keywordInput.value.trim()) params.set("q", keywordInput.value.trim());

  showStatus(statusBox, "공고를 불러오는 중이다.");
  listBox.replaceChildren();
  try {
    let jobs = await callApi(`/api/jobs?${params}`);
    if (onlyFavorites.checked) {
      const favorites = loadFavorites();
      jobs = jobs.filter((job) => favorites.includes(job.id));
    }
    listBox.append(...jobs.map(renderJob));
    showStatus(statusBox, jobs.length ? `공고 ${jobs.length}건` : "조건에 맞는 공고가 없다.");
  } catch (error) {
    showStatus(statusBox, `공고를 불러오지 못하였다: ${error.message}`, true);
  }
}

// 분야 목록은 처음 한 번 전체 공고에서 뽑는다.
async function loadFields() {
  try {
    const jobs = await callApi("/api/jobs");
    const fields = [...new Set(jobs.map((job) => job.field))].sort();
    for (const field of fields) {
      const option = el("option", field);
      option.value = field;
      fieldSelect.append(option);
    }
  } catch {
    // 분야 목록을 못 불러와도 목록 화면은 쓸 수 있다. 오류는 loadJobs()가 알린다.
  }
}

document.getElementById("filters").addEventListener("submit", (event) => {
  event.preventDefault();
  loadJobs();
});
onlyFavorites.addEventListener("change", loadJobs);

loadFields();
loadJobs();
