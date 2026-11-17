// 공고 상세 화면: 공고 하나를 보여 주고, 관심 표시와 요약을 한다.

const statusBox = document.getElementById("status");
const jobId = Number(new URLSearchParams(location.search).get("id"));
let currentJob = null;

function fillList(id, items) {
  const list = document.getElementById(id);
  list.replaceChildren(...(items.length ? items : ["(공고에 없음)"]).map((text) => el("li", text)));
}

function updateFavoriteButton() {
  const button = document.getElementById("favorite");
  const on = isFavorite(jobId);
  button.textContent = on ? "★ 관심 공고" : "☆ 관심 공고";
  button.setAttribute("aria-pressed", String(on));
}

// 요약 API에 보낼 글: 제목, 기업, 마감일, 본문을 잇는다.
function jobText(job) {
  return `${job.title} / ${job.company}\n마감일: ${job.deadline}\n${job.description}`;
}

async function summarize() {
  const button = document.getElementById("summarize");
  button.disabled = true;
  showStatus(statusBox, "요약하는 중이다.");
  try {
    const result = await postJson("/api/summary", { text: jobText(currentJob) });
    fillList("sum-duties", result.duties);
    fillList("sum-qualifications", result.qualifications);
    document.getElementById("sum-deadline").textContent = result.deadline || "(공고에 없음)";
    fillList("sum-cautions", result.cautions);
    document.getElementById("sum-meta").textContent =
      `프롬프트 ${result.prompt_version} · 모델 ${result.model}. 요약은 AI가 만든 것이므로 공고 본문과 대조한다.`;
    document.getElementById("summary").hidden = false;
    showStatus(statusBox, "");
  } catch (error) {
    showStatus(statusBox, `요약하지 못하였다: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function loadJob() {
  if (!jobId) {
    showStatus(statusBox, "공고 번호가 없다. 목록에서 공고를 고른다.", true);
    return;
  }
  showStatus(statusBox, "공고를 불러오는 중이다.");
  try {
    currentJob = await callApi(`/api/jobs/${jobId}`);
  } catch (error) {
    showStatus(statusBox, `공고를 불러오지 못하였다: ${error.message}`, true);
    return;
  }
  document.title = `${currentJob.title} - jobprep`;
  document.getElementById("job-title").textContent = currentJob.title;
  document.getElementById("job-meta").textContent =
    `${currentJob.company} · ${currentJob.field} · ${currentJob.location} · ${currentJob.employment_type} · ${currentJob.salary}`;
  document.getElementById("job-deadline").textContent =
    `게시 ${currentJob.posted_at} · 마감 ${currentJob.deadline} (${dDay(currentJob.days_left)})`;
  document.getElementById("job-description").textContent = currentJob.description;
  document.getElementById("job").hidden = false;
  updateFavoriteButton();
  showStatus(statusBox, "");
}

document.getElementById("favorite").addEventListener("click", () => {
  toggleFavorite(jobId);
  updateFavoriteButton();
});
document.getElementById("summarize").addEventListener("click", summarize);

loadJob();
