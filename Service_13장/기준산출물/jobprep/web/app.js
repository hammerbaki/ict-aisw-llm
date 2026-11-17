// 13장 평가용 견본. 서버 없이 브라우저에서 열린다.
// AI 기능은 실제 모델을 부르지 않고 정해진 규칙으로 흉내 낸다(모의 모드와 같은 구실).
// 주의: 이 견본에는 평가 실습을 위해 사용성 문제를 일부러 남겨 두었다. 고치지 말고 평가한다.

const STORE_KEY = "jobprep-tracker";
let visibleJobs = JOBS.slice();

// ---------- 탭 ----------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== tab.dataset.tab));
  });
});

// ---------- SCR-01 공고 목록 ----------
function dday(due) {
  const today = new Date().toISOString().slice(0, 10);
  return Math.round((new Date(due) - new Date(today)) / 86400000);
}

function renderJobs() {
  const list = document.getElementById("job-list");
  list.innerHTML = "";
  visibleJobs.forEach((job) => {
    const li = document.createElement("li");
    li.className = "card";
    li.innerHTML =
      `<div class="meta">공고번호 ${job.id} · 등록 ${job.posted.replaceAll("-", ".")} · 조회 ${job.views} · 담당 ${job.manager}</div>` +
      `<strong>${job.company}</strong> ${job.title} <span class="region">[${job.region}]</span>` +
      `<div class="due">마감 ${job.due.slice(5).replace("-", "/")} (D-${dday(job.due)})</div>` +
      `<button class="parse">JD 파싱</button> <button class="save">Apply Tracker에 저장</button>`;
    li.querySelector(".parse").addEventListener("click", () => summarize(job));
    li.querySelector(".save").addEventListener("click", () => {
      addTracker({ company: job.company, due: job.due, memo: job.title });
    });
    list.appendChild(li);
  });
}

document.getElementById("search").addEventListener("click", () => {
  const q = document.getElementById("q").value.trim();
  visibleJobs = JOBS.filter((j) => (j.company + j.title + j.body).includes(q));
  renderJobs();
});

document.getElementById("apply-filter").addEventListener("click", () => {
  const region = document.getElementById("region").value;
  visibleJobs = JOBS.filter((j) => region === "ALL" || j.region === region);
  document.getElementById("region").value = "ALL";
  renderJobs();
});

// ---------- AI 요약 (모의) ----------
function fakeSummary(job) {
  const sentences = job.body.split(". ").filter((s) => /자격|우대|전형/.test(s));
  return sentences.map((s) => "• " + s.replace(/\.$/, "")).join("<br>");
}

function summarize(job) {
  const box = document.getElementById("summary-box");
  const out = document.getElementById("summary-out");
  box.hidden = false;
  setTimeout(() => {
    const result = job.body ? fakeSummary(job) : undefined;
    out.innerHTML += `<p><strong>${job.company}</strong><br>${result}</p>`;
  }, 2500);
}

// ---------- SCR-03 지원 일정 ----------
function loadTracker() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveTracker(items) {
  localStorage.setItem(STORE_KEY, JSON.stringify(items));
}

function addTracker(item) {
  const items = loadTracker();
  items.push(item);
  saveTracker(items);
  renderTracker();
}

function renderTracker() {
  const list = document.getElementById("tracker-list");
  list.innerHTML = "";
  loadTracker().forEach((item, index) => {
    const li = document.createElement("li");
    li.className = "card";
    li.innerHTML = `<strong>${item.company}</strong> 마감 ${item.due} ${item.memo || ""} <button class="del">X</button>`;
    li.querySelector(".del").addEventListener("click", () => {
      const items = loadTracker();
      items.splice(index, 1);
      saveTracker(items);
      renderTracker();
    });
    list.appendChild(li);
  });
}

document.getElementById("add-form").addEventListener("submit", (e) => {
  e.preventDefault();
  addTracker({
    company: document.getElementById("t-company").value,
    due: document.getElementById("t-due").value,
    memo: document.getElementById("t-memo").value,
  });
  e.target.reset();
});

// ---------- SCR-06 자료 묻기 (모의 질의응답) ----------
document.getElementById("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = document.getElementById("question").value;
  const answer = document.getElementById("answer");
  const hit = GUIDES.find((g) => g.keywords.some((k) => q.includes(k)));
  answer.textContent = hit ? hit.text : "Error: 422 Unprocessable Entity";
});

renderJobs();
renderTracker();
