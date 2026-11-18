// 13장 기준산출물: 5장 서비스 1(공고 모아보기 웹)의 견본.
// 자료(data/jobs.json)는 지어낸 것이다. 13장의 평가 실습을 위해 사용성 문제를 일부러 남겨 두었다.
// 평가하기 전에 이 코드를 읽지 않는다.

let DATA = null;
let visible = [];

// 기준일: 주소의 ?today=YYYY-MM-DD, 없으면 자료를 받은 날(fetched).
// 견본 자료가 시간이 지나도 같은 화면을 보이게 하려는 것이다.
function baseDate() {
  const q = new URLSearchParams(location.search).get("today");
  return q || DATA.fetched.slice(0, 10);
}

// "27-05-19" → "2027-05-19". 날짜가 아니면 null(예: "채용시까지").
function toDate(closeDt) {
  return /^\d{2}-\d{2}-\d{2}$/.test(closeDt) ? "20" + closeDt : null;
}

function daysLeft(closeDt) {
  const d = toDate(closeDt);
  if (!d) return null;
  return Math.round((new Date(d) - new Date(baseDate())) / 86400000);
}

// REQ-02, REQ-10: 마감일순. 날짜가 아닌 마감일은 뒤로 보낸다.
function sortJobs(jobs, how) {
  const copy = jobs.slice();
  if (how === "close") {
    copy.sort((a, b) => (toDate(a.closeDt) || "9999") < (toDate(b.closeDt) || "9999") ? -1 : 1);
  } else {
    copy.sort((a, b) => (a.regDt < b.regDt ? 1 : -1));
  }
  return copy;
}

function dueText(job) {
  const left = daysLeft(job.closeDt);
  if (left === null) return "마감 상시";                       // REQ-09
  const label = "마감 " + job.closeDt.slice(3).replace("-", "/");
  if (left >= 0 && left <= 3) return `${label} <span class="soon">마감 임박 D-${left}</span>`;  // REQ-03
  return label;
}

function render() {
  const list = document.getElementById("job-list");
  const msg = document.getElementById("message");
  list.innerHTML = "";
  const shown = sortJobs(visible, document.getElementById("sort").value);
  document.getElementById("count").textContent = `공고 ${shown.length}건`;
  if (shown.length === 0) {
    msg.hidden = false;
    msg.textContent = "조건에 맞는 공고가 없습니다.";             // REQ-08
    return;
  }
  msg.hidden = true;
  shown.forEach((job) => {
    const li = document.createElement("li");
    li.className = "card";
    li.innerHTML =
      `<div class="meta">${job.wantedAuthNo} · 등록 ${job.regDt}</div>` +
      `<div class="title"><strong>${job.company}</strong> ${job.title}</div>` +
      `<div class="info">${job.region} · ${job.career} · ${job.salTpNm} ${job.sal}</div>` +
      `<div class="due">${dueText(job)}</div>`;
    list.appendChild(li);
  });
}

// REQ-04, REQ-05, REQ-06: 검색 단추를 누르면 세 조건으로 거른다.
function applyFilters() {
  const q = document.getElementById("q").value.trim();
  const region = document.getElementById("region").value;
  const career = document.getElementById("career").value;
  visible = DATA.jobs.filter((j) =>
    (!q || (j.title + j.company).includes(q)) &&
    (!region || j.region.includes(region)) &&
    (!career || j.career === career));
  render();
}

document.getElementById("search").addEventListener("click", applyFilters);
document.getElementById("sort").addEventListener("change", render);

fetch("data/jobs.json")
  .then((r) => r.json())
  .then((d) => {
    DATA = d;
    visible = d.jobs.slice();
    document.getElementById("source").textContent = `자료: ${d.source} · 받은 시각 ${d.fetched}`;  // REQ-07
    render();
  })
  .catch(() => {
    document.getElementById("message").hidden = false;
    document.getElementById("message").textContent =
      "공고 자료를 불러오지 못했습니다. 로컬 서버로 열었는지 확인하십시오.";
  });
