// jobprep 프로토타입의 동작. 빌드 도구 없이 브라우저에서 바로 연다.
// 주소 뒤에 ?state=empty, ?state=loading, ?state=error 를 붙이면 화면 명세의 상태를 볼 수 있다.
// SCR-02는 ?state=summary-error(요약 실패), ?state=summary-limit(사용 한도), SCR-04는 ?state=store-error(저장 실패)도 받는다.

const params = new URLSearchParams(location.search);
const forcedState = params.get("state");
const STORE_KEY = "jobprep-proto-schedule";
const SAVED_KEY = "jobprep-proto-saved";

// ---------- 공통 도우미 ----------
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c);
  return node;
}

function daysLeft(deadline) {
  const ms = new Date(deadline + "T00:00:00") - new Date(TODAY + "T00:00:00");
  return Math.round(ms / 86400000);
}

function formatDate(date) {
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  const d = new Date(date + "T00:00:00");
  return `${date}(${days[d.getDay()]})`;
}

// 공고의 상태: 접수 시작일 전이면 접수예정, 마감일이 지났으면 마감, 그 사이면 접수중(REQ-005)
function jobStatus(job) {
  if (TODAY < job.opens) return "접수예정";
  if (TODAY > job.deadline) return "마감";
  return "접수중";
}

// 마감 3일 이내면 색만이 아니라 글자로도 알린다(REQ-003, WCAG 1.4.1)
function deadlineBadge(deadline) {
  const left = daysLeft(deadline);
  if (left < 0 || left > 3) return null;
  return el("span", { class: "badge", text: left === 0 ? "마감 임박 D-day" : `마감 임박 D-${left}` });
}

function readList(key) {
  try { return JSON.parse(sessionStorage.getItem(key) || "[]"); } catch (e) { return []; }
}

function loadSchedule() {
  return SCHEDULE_SEED.concat(readList(STORE_KEY));
}

// 저장에 성공하면 true. 저장소를 쓸 수 없으면 false를 돌려주고 화면이 까닭을 알린다(REQ-026)
function saveScheduleItem(item) {
  if (forcedState === "store-error") return false;
  try {
    const saved = readList(STORE_KEY);
    saved.push(item);
    sessionStorage.setItem(STORE_KEY, JSON.stringify(saved));
    return true;
  } catch (e) {
    return false;
  }
}

// ---------- SCR-01 공고 목록 ----------
function initJobList() {
  const list = document.getElementById("job-list");
  const status = document.getElementById("result-status");
  const area = document.getElementById("result-area");
  const form = document.getElementById("filter-form");

  function render() {
    list.replaceChildren();
    area.querySelectorAll(".notice, .skeleton").forEach((n) => n.remove());

    if (forcedState === "loading") {
      area.setAttribute("aria-busy", "true");
      status.textContent = "공고를 불러오는 중이에요";
      for (let i = 0; i < 3; i++) area.append(el("div", { class: "skeleton", "aria-hidden": "true" }));
      return;
    }
    area.removeAttribute("aria-busy");
    if (forcedState === "error") {              // 공고 자료를 읽지 못했을 때(REQ-004)
      status.textContent = "";
      const retry = el("a", { href: "index.html", text: "다시 불러오기" });
      area.append(el("div", { class: "notice notice--error", role: "alert" },
        el("p", { text: "공고 자료를 불러오지 못했어요. 인터넷 연결을 확인한 뒤 다시 불러와 주세요." }), retry));
      return;
    }

    const q = form.q.value.trim().toLowerCase();
    const st = form.status.value;
    const region = form.region.value;
    const role = form.role.value;
    const source = forcedState === "empty" ? [] : JOBS;
    const hits = source
      .filter((j) => !q || [j.title, j.company].some((s) => s.toLowerCase().includes(q)))   // REQ-006
      .filter((j) => !st || jobStatus(j) === st)                                             // REQ-005
      .filter((j) => !region || j.region === region)                                         // REQ-028
      .filter((j) => !role || j.role === role)                                               // REQ-028
      .sort((a, b) => a.deadline.localeCompare(b.deadline));                                 // REQ-002

    status.textContent = `공고 ${hits.length}건`;                                           // REQ-029
    if (hits.length === 0) {                                                                 // REQ-007
      const reset = el("button", { type: "button", class: "btn btn--secondary", text: "조건 모두 지우기" });
      reset.addEventListener("click", () => { form.reset(); render(); form.q.focus(); });
      area.append(el("div", { class: "notice notice--empty" },
        el("h2", { text: "조건에 맞는 공고가 없어요" }),
        el("p", { text: "검색어를 줄이거나 상태·지역·직무를 「전체」로 바꿔 보세요." }), reset));
      return;
    }
    for (const j of hits) {                                                                  // REQ-001
      const title = el("h2", {}, el("a", { href: `job.html?id=${j.id}`, text: j.title }));
      const meta = el("p", { class: "meta", text: `${j.company} · ${j.region} · ${j.role}` });
      const dl = el("p", { text: `${jobStatus(j)} · 마감 ${formatDate(j.deadline)} ` });
      const badge = deadlineBadge(j.deadline);
      if (badge) dl.append(badge);
      list.append(el("li", {}, el("article", { class: "card" }, title, meta, dl)));
    }
  }

  // 필터를 바꾸면 목록만 갱신하고 화면은 옮기지 않는다(WCAG 3.2.2). 결과 수는 상태 영역이 읽어 준다.
  form.addEventListener("input", render);
  form.addEventListener("submit", (e) => { e.preventDefault(); render(); });
  render();
}

// ---------- SCR-02 공고 상세 ----------
function initJobDetail() {
  const id = params.get("id");
  const job = id ? JOBS.find((j) => j.id === id) : JOBS[0];
  if (!job) {                                  // 없는 공고 번호(REQ-037)
    document.getElementById("job-detail").hidden = true;
    document.getElementById("not-found").hidden = false;
    return;
  }
  document.title = `${job.title} - 공고 상세 - jobprep`;
  document.getElementById("job-title").textContent = job.title;
  document.getElementById("job-company").textContent = job.company;
  document.getElementById("job-status").textContent = jobStatus(job);
  document.getElementById("job-region").textContent = job.region;
  document.getElementById("job-role").textContent = job.role;
  const dd = document.getElementById("job-deadline");
  dd.textContent = formatDate(job.deadline) + " ";
  const badge = deadlineBadge(job.deadline);
  if (badge) dd.append(badge);
  const req = document.getElementById("job-requirements");
  job.requirements.forEach((r) => req.append(el("li", { text: r })));
  const original = document.getElementById("original-text");
  job.paragraphs.forEach((p, i) => original.append(el("p", { id: `p${i + 1}`, tabindex: "-1" },
    el("span", { class: "visually-hidden", text: `원문 ${i + 1}문단. ` }), p)));
  document.getElementById("add-schedule").href = `schedule-new.html?job=${job.id}`;

  // 관심 공고 저장과 해제(REQ-008, REQ-038). 프로토타입은 sessionStorage에 둔다
  const saveBtn = document.getElementById("save-toggle");
  const saveMsg = document.getElementById("save-message");
  function isSaved() { return readList(SAVED_KEY).includes(job.id); }
  function showSave(saved) {
    saveBtn.textContent = saved ? "관심 해제" : "관심 공고 저장";
    saveBtn.setAttribute("aria-pressed", String(saved));
  }
  showSave(isSaved());
  saveBtn.addEventListener("click", () => {
    const ids = readList(SAVED_KEY);
    const next = ids.includes(job.id) ? ids.filter((x) => x !== job.id) : ids.concat(job.id);
    try { sessionStorage.setItem(SAVED_KEY, JSON.stringify(next)); } catch (e) {
      saveMsg.textContent = "관심 공고를 저장하지 못했어요. 브라우저가 사이트 데이터 저장을 막고 있어요.";
      return;
    }
    const saved = next.includes(job.id);
    showSave(saved);
    saveMsg.textContent = saved ? "관심 공고에 저장했어요." : "관심 공고에서 뺐어요.";
  });

  const btn = document.getElementById("summary-btn");
  const status = document.getElementById("summary-status");
  const output = document.getElementById("summary-output");
  let busy = false;

  // 가짜 응답이 없는 공고는 원문 문단의 첫 문장으로 같은 모양의 응답을 만든다
  function fakeSummary() {
    if (FAKE_SUMMARY[job.id]) return FAKE_SUMMARY[job.id];
    const first = (n) => job.paragraphs[n - 1].split(". ")[0].replace(/\.?$/, ".");
    return [
      { item: "자격 요건", text: first(3), evidence: first(3), source: 3 },
      { item: "근무 조건", text: first(2), evidence: first(2), source: 2 },
      { item: "제출 서류", text: null },
      { item: "접수 마감일", text: first(4), evidence: first(4), source: 4 }
    ];
  }

  function showSummary() {
    const ol = el("ol");
    for (const part of fakeSummary()) {
      const li = el("li", {}, el("h3", { text: part.item }));
      if (!part.text) {                        // 원문에 정보가 없는 항목(REQ-015)
        li.append(el("p", { class: "missing", text: "공고에 없음" }));
      } else {                                 // 항목 아래에 근거 문장과 그 문단으로 가는 링크(REQ-014)
        li.append(el("p", { text: part.text }));
        const link = el("a", { href: `#p${part.source}`, class: "source-link", text: `원문 ${part.source}문단` });
        li.append(el("p", { class: "evidence" }, `근거: 「${part.evidence}」 `, link));
      }
      ol.append(li);
    }
    output.replaceChildren(
      el("p", { class: "ai-note", text: "AI가 만든 요약이에요. 마감일과 자격 요건은 근거 문장과 원문 문단을 눌러 확인해 주세요." }),
      ol);
    status.textContent = "요약을 만들었어요. 네 항목이에요.";
    btn.querySelector(".label").textContent = "다시 만들기";
  }

  function showError() {                       // 응답 실패, 시간 초과(REQ-024). 원문은 그대로 둔다
    output.replaceChildren(el("div", { class: "notice notice--error" },
      el("p", { text: "요약을 만들지 못했어요. 잠시 뒤 「다시 시도」를 눌러 주세요. 원문은 그대로 읽을 수 있어요." })));
    status.textContent = "요약을 만들지 못했어요.";
    btn.querySelector(".label").textContent = "다시 시도";
  }

  function showLimit() {                       // 사용 한도(REQ-025). 요청을 보내지 않는다
    output.replaceChildren(el("div", { class: "notice notice--error" },
      el("p", { text: "오늘 쓸 수 있는 요약 횟수를 다 썼어요. 내일 0시부터 다시 만들 수 있어요. 원문은 그대로 읽을 수 있어요." })));
    status.textContent = "요약 사용 한도에 닿았어요.";
  }

  btn.addEventListener("click", () => {
    if (busy) return;                       // 생성 중에는 거듭 보내지 않는다(REQ-016)
    if (forcedState === "summary-limit") { showLimit(); return; }
    busy = true;
    btn.setAttribute("aria-disabled", "true");
    btn.setAttribute("aria-busy", "true");
    btn.querySelector(".label").textContent = "요약을 만드는 중";
    status.textContent = "요약을 만드는 중이에요. 보통 10초 안에 끝나요.";
    setTimeout(() => {
      busy = false;
      btn.removeAttribute("aria-disabled");
      btn.removeAttribute("aria-busy");
      if (forcedState === "summary-error") showError(); else showSummary();
    }, 1200);
  });

  // 근거 문단 링크를 누르면 그 문단으로 초점을 옮긴다(키보드 사용자도 원문 위치에 도착한다)
  output.addEventListener("click", (e) => {
    const a = e.target.closest("a.source-link");
    if (!a) return;
    const target = document.querySelector(a.getAttribute("href"));
    if (target) setTimeout(() => target.focus(), 0);
  });
}

// ---------- SCR-03 지원 일정 ----------
function initSchedule() {
  const list = document.getElementById("schedule-list");
  const area = document.getElementById("schedule-area");
  const status = document.getElementById("schedule-status");
  let items = forcedState === "empty" ? [] : loadSchedule();

  if (params.get("saved") === "1") {
    const msg = document.getElementById("saved-message");
    msg.hidden = false;
    msg.querySelector("p").textContent = "지원 일정을 저장했어요.";
  }

  function render() {
    list.replaceChildren();
    area.querySelectorAll(".notice--empty").forEach((n) => n.remove());
    items.sort((a, b) => a.date.localeCompare(b.date));      // 날짜순(REQ-010)
    status.textContent = `지원 일정 ${items.length}건`;
    if (items.length === 0) {
      area.append(el("div", { class: "notice notice--empty" },
        el("h2", { text: "아직 지원 일정이 없어요" }),
        el("p", { text: "관심 있는 공고에서 「지원 일정에 추가」를 누르면 날짜순으로 여기에 모여요." }),
        el("p", {}, el("a", { class: "btn btn--primary", href: "index.html", text: "공고 찾아보기" }), " ",
          el("a", { class: "btn btn--secondary", href: "schedule-new.html", text: "직접 등록하기" }))));
      return;
    }
    for (const it of items) {
      const del = el("button", { type: "button", class: "btn btn--secondary", text: "삭제" });
      del.setAttribute("aria-label", `삭제: ${it.company} ${it.title} ${it.kind}`);
      del.addEventListener("click", () => {
        // 삭제 전에 확인을 받는다(REQ-032). 프로토타입은 브라우저 기본 확인 창을 쓴다
        if (!confirm(`「${it.title}」의 ${it.kind} 일정을 삭제할까요? 삭제하면 되돌릴 수 없어요.`)) return;
        items = items.filter((x) => x !== it);
        render();
        status.textContent = `일정을 삭제했어요. 지원 일정 ${items.length}건`;
        document.getElementById("schedule-heading").focus();
      });
      const title = it.jobId
        ? el("h2", {}, el("a", { href: `job.html?id=${it.jobId}`, text: it.title }))
        : el("h2", { text: it.title });
      list.append(el("li", {}, el("article", { class: "card" },
        title, el("p", { class: "meta", text: `${it.company} · ${it.kind}` }),
        el("p", { text: formatDate(it.date) }),
        el("div", { class: "card__actions" }, del))));
    }
  }
  render();
}

// ---------- SCR-04 지원 일정 등록 ----------
function initScheduleNew() {
  const form = document.getElementById("schedule-form");
  const summary = document.getElementById("error-summary");
  const job = JOBS.find((j) => j.id === params.get("job"));
  if (job) {                                // 공고에서 왔으면 이미 아는 값을 채운다(WCAG 3.3.7)
    form.company.value = job.company;
    form.title.value = job.title;
    form.date.value = job.deadline;
  }

  const rules = [
    { name: "company", check: (v) => v.trim() !== "", msg: "모집기관을 입력해 주세요." },
    { name: "title", check: (v) => v.trim() !== "", msg: "공고 제목을 입력해 주세요." },
    { name: "date", check: (v) => v !== "", msg: "날짜를 골라 주세요. 예: 2027-04-30" },
    { name: "date", check: (v) => v === "" || v >= TODAY,
      msg: `날짜가 지났어요. 오늘(${TODAY}) 이후 날짜를 골라 주세요.` }
  ];

  function setError(input, message) {
    const errId = `${input.id}-error`;
    let p = document.getElementById(errId);
    const hintId = `${input.id}-hint`;
    const described = document.getElementById(hintId) ? [hintId] : [];
    if (message) {
      if (!p) {
        p = el("p", { id: errId, class: "error" });
        input.insertAdjacentElement("afterend", p);
      }
      p.textContent = "오류: " + message;
      input.setAttribute("aria-invalid", "true");
      described.push(errId);
    } else {
      if (p) p.remove();
      input.removeAttribute("aria-invalid");
    }
    if (described.length) input.setAttribute("aria-describedby", described.join(" "));
    else input.removeAttribute("aria-describedby");
  }

  function validate() {
    const errors = [];
    const seen = new Set();
    for (const r of rules) {
      const input = form[r.name];
      if (seen.has(r.name)) continue;
      if (!r.check(input.value)) { errors.push({ input, msg: r.msg }); seen.add(r.name); }
    }
    for (const name of ["company", "title", "date"]) {
      const e = errors.find((x) => x.input.name === name);
      setError(form[name], e ? e.msg : null);
    }
    return errors;
  }

  function showSummaryBox(heading, items) {
    const ul = el("ul");
    for (const it of items) ul.append(el("li", {}, it));
    summary.replaceChildren(el("h2", { text: heading }), ul);
    summary.hidden = false;
    summary.focus();                         // 오류 요약으로 초점을 옮긴다. 입력한 값은 지우지 않는다
  }

  // 검사는 「일정 저장」을 누를 때만 한다. 칸을 떠날 때마다 검사하던 판에서는 오류 문장이 사라지며
  // 아래 버튼이 위로 밀려, 저장 버튼을 누른 클릭이 빗나갔다(8장 Playwright 점검에서 찾은 결함).

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const errors = validate();
    if (errors.length) {                       // 입력 오류(REQ-031)
      showSummaryBox(`입력을 확인해 주세요 (${errors.length}건)`, errors.map((err) => {
        const a = el("a", { href: `#${err.input.id}`, text: err.msg });
        a.addEventListener("click", (ev) => { ev.preventDefault(); err.input.focus(); });
        return a;
      }));
      return;
    }
    summary.hidden = true;
    const ok = saveScheduleItem({
      id: "N" + Date.now(), jobId: job ? job.id : "", company: form.company.value.trim(),
      title: form.title.value.trim(), kind: form.kind.value, date: form.date.value
    });
    if (!ok) {                                 // 저장 실패와 그 까닭(REQ-026)
      showSummaryBox("지원 일정을 저장하지 못했어요",
        ["브라우저가 이 사이트의 데이터 저장을 막고 있어요. 브라우저 설정에서 사이트 데이터 저장을 허용한 뒤 다시 저장해 주세요. 입력한 내용은 그대로 있어요."]);
      return;
    }
    location.href = "schedule.html?saved=1";
  });
}

// ---------- 시작 ----------
const page = document.body.dataset.page;
({ "job-list": initJobList, "job-detail": initJobDetail, "schedule": initSchedule,
   "schedule-new": initScheduleNew }[page] || (() => {}))();
