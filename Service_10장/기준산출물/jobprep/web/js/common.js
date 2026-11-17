/* 모든 화면이 함께 쓰는 기능: 공고 자료 읽기, 브라우저 저장소, 기준일, 마감 표시.
   화면에 글자를 넣을 때는 textContent 만 쓴다(innerHTML 금지, CLAUDE.md 의 금지 사항). */

const STORAGE_KEYS = {
  saved: "jobprep:saved",       // 관심 공고 번호의 배열
  schedule: "jobprep:schedule", // 지원 일정의 배열
};

/* 공고 자료(data/jobs.json)를 읽는다. 상대 경로로 부른다(프로젝트 사이트의 하위 경로에서도 동작). */
async function loadJobs() {
  const response = await fetch("data/jobs.json");
  if (!response.ok) {
    throw new Error("공고 자료를 읽지 못했습니다: " + response.status);
  }
  const data = await response.json();
  return data.jobs;
}

/* 저장소에서 배열을 읽는다. 값이 없거나 깨져 있으면 빈 배열을 돌려준다. */
function readList(key) {
  try {
    const raw = localStorage.getItem(key);
    const value = raw ? JSON.parse(raw) : [];
    return Array.isArray(value) ? value : [];
  } catch (error) {
    return [];
  }
}

/* 저장소에 배열을 쓴다. 용량 초과나 저장 차단이면 false 를 돌려준다. */
function writeList(key, list) {
  try {
    localStorage.setItem(key, JSON.stringify(list));
    return true;
  } catch (error) {
    return false;
  }
}

function getSavedIds() {
  return readList(STORAGE_KEYS.saved);
}

function isSaved(jobId) {
  return getSavedIds().includes(jobId);
}

/* 관심 공고를 저장하거나 해제하고, 바뀐 뒤의 상태(true=저장됨)를 돌려준다. */
function toggleSaved(jobId) {
  const ids = getSavedIds();
  const next = ids.includes(jobId) ? ids.filter((id) => id !== jobId) : ids.concat(jobId);
  writeList(STORAGE_KEYS.saved, next);
  return next.includes(jobId);
}

/* 기준일: 주소에 ?today=YYYY-MM-DD 가 있으면 그 날, 없으면 오늘(명세 REQ-003, 화면 명세의 검사용 약속). */
function getToday() {
  const param = new URLSearchParams(location.search).get("today");
  if (param && /^\d{4}-\d{2}-\d{2}$/.test(param)) {
    return param;
  }
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/* 두 날짜(YYYY-MM-DD) 사이의 날 수. 시간대의 영향을 받지 않도록 UTC 로 계산한다. */
function daysBetween(from, to) {
  const a = Date.UTC(...from.split("-").map((v, i) => (i === 1 ? Number(v) - 1 : Number(v))));
  const b = Date.UTC(...to.split("-").map((v, i) => (i === 1 ? Number(v) - 1 : Number(v))));
  return Math.round((b - a) / 86400000);
}

/* 마감 상태: 마감일 없음(상시), 지남(마감), 0~3일 남음(임박), 그 밖(보통). */
function deadlineStatus(deadline, today) {
  if (!deadline) {
    return { kind: "always", label: "" };
  }
  const left = daysBetween(today, deadline);
  if (left < 0) {
    return { kind: "closed", label: "마감" };
  }
  if (left <= 3) {
    return { kind: "soon", label: left === 0 ? "마감 임박 D-day" : `마감 임박 D-${left}` };
  }
  return { kind: "normal", label: "" };
}

/* 마감 표시 요소를 만든다. 표시할 것이 없으면 null. */
function makeDeadlineBadge(deadline, today) {
  const status = deadlineStatus(deadline, today);
  if (!status.label) {
    return null;
  }
  const badge = document.createElement("span");
  badge.className = `deadline-badge deadline-${status.kind}`;
  badge.textContent = status.label;
  return badge;
}

function formatDeadline(deadline) {
  return deadline ? `마감 ${deadline}` : "상시 채용";
}

/* 마감일 순 정렬: 빠른 날짜 먼저, 상시(마감일 없음)는 맨 뒤. */
function compareByDeadline(a, b) {
  if (a.deadline === b.deadline) return a.id.localeCompare(b.id);
  if (!a.deadline) return 1;
  if (!b.deadline) return -1;
  return a.deadline.localeCompare(b.deadline);
}

/* 요소를 만들고 글자를 넣는 도우미(textContent 사용). */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/* 같은 기준일을 다음 화면에도 넘긴다(검사와 시연에서 날짜를 고정하기 위해). */
function withToday(href) {
  const param = new URLSearchParams(location.search).get("today");
  if (!param) return href;
  return href + (href.includes("?") ? "&" : "?") + "today=" + encodeURIComponent(param);
}
