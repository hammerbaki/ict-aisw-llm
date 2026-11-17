/* SCR-01 공고 목록: 마감일 순, 검색, 분야·지역 고르기, 공고 수, 빈 상태, 마감 표시 (REQ-001~004, REQ-006, REQ-007, REQ-028, REQ-029) */
let allJobs = [];

function fillOptions(select, values) {
  for (const value of values) {
    const option = el("option", "", value);
    option.value = value;
    select.append(option);
  }
}

function matches(job, keyword, category, region) {
  const text = `${job.title} ${job.company}`.toLowerCase();   // REQ-006: 제목이나 모집기관(기업)
  if (keyword && !text.includes(keyword.toLowerCase())) return false;
  if (category && job.category !== category) return false;
  if (region && job.region !== region) return false;
  return true;
}

function makeCard(job, today) {
  const item = el("li", "job-card");
  item.dataset.jobId = job.id;
  const link = el("a", "job-link");
  link.href = withToday(`detail.html?id=${encodeURIComponent(job.id)}`);
  link.append(el("span", "job-title", job.title));
  item.append(link);
  item.append(el("p", "job-company", job.company));
  const meta = el("p", "job-meta");
  meta.append(el("span", "job-category", job.category));
  meta.append(el("span", "job-region", job.region));
  meta.append(el("span", "job-deadline", formatDeadline(job.deadline)));
  const badge = makeDeadlineBadge(job.deadline, today);
  if (badge) meta.append(badge);
  item.append(meta);
  return item;
}

function render() {
  const keyword = document.getElementById("search-input").value.trim();
  const category = document.getElementById("filter-category").value;
  const region = document.getElementById("filter-region").value;
  const today = getToday();
  const shown = allJobs.filter((job) => matches(job, keyword, category, region)).sort(compareByDeadline);

  const list = document.getElementById("job-list");
  list.replaceChildren(...shown.map((job) => makeCard(job, today)));
  document.getElementById("result-count").textContent = `공고 ${shown.length}건`;
  document.getElementById("empty-state").hidden = shown.length > 0;
}

function resetFilters() {
  document.getElementById("search-input").value = "";
  document.getElementById("filter-category").value = "";
  document.getElementById("filter-region").value = "";
  render();
}

async function start() {
  try {
    allJobs = await loadJobs();
  } catch (error) {
    const box = document.getElementById("load-error");
    box.textContent = "공고 자료를 불러오지 못했습니다. 로컬 서버로 열었는지 확인하십시오.";
    box.hidden = false;
    document.getElementById("result-count").textContent = "공고 0건";
    return;
  }
  fillOptions(document.getElementById("filter-category"), [...new Set(allJobs.map((j) => j.category))]);
  fillOptions(document.getElementById("filter-region"), [...new Set(allJobs.map((j) => j.region))]);
  document.getElementById("search-input").addEventListener("input", render);
  document.getElementById("filter-category").addEventListener("change", render);
  document.getElementById("filter-region").addEventListener("change", render);
  document.getElementById("search-form").addEventListener("submit", (event) => event.preventDefault());
  document.getElementById("reset-filters").addEventListener("click", resetFilters);
  render();
}

start();
