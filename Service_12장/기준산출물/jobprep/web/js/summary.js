/* 10장 정답 예시: 공고 상세 화면의 「요약 보기」 버튼을 요약 API에 연결한다.
   원칙 1. 브라우저는 우리 서버(/api/summary)만 부른다. 키와 Claude API 주소는 여기에 없다.
   원칙 2. 모델 출력은 신뢰하지 않는 입력으로 다룬다. HTML로 해석하지 않고 글자로만 넣는다.
   원칙 3. 기다리는 동안(생성 중)과 실패했을 때의 상태를 화면에 알린다.
   common.js의 loadJobs()를 쓴다(detail.html이 common.js를 먼저 불러온다). */

const SUMMARY_FIELDS = [
  ["핵심업무", "핵심 업무"],
  ["자격요건", "자격 요건"],
  ["주의점", "주의점"],
];

/* 9장의 공고 자료는 칸으로 나뉜 JSON이다. 요약 API가 받는 「공고 원문」 모양의 글로 잇는다. */
function jobToText(job) {
  const lines = [`[회사] ${job.company}`, `[직무] ${job.title}`, "[주요 업무]", `- ${job.summary}`, "[자격 요건]"];
  for (const r of job.requirements || []) lines.push(`- ${r}`);
  if ((job.preferred || []).length) {
    lines.push("[우대 사항]");
    for (const p of job.preferred) lines.push(`- ${p}`);
  }
  lines.push("[근무 조건]", `- 지역: ${job.region}`, `- 고용 형태: ${job.employment_type}`);
  lines.push("[접수 기간]", job.deadline ? `- ~ ${job.deadline}` : "- 상시 채용");
  return lines.join("\n");
}

function renderSummary(box, summary, meta) {
  box.replaceChildren(); // 이전 결과를 지운다
  const deadline = document.createElement("p");
  deadline.textContent = `마감일: ${summary["마감일"] ?? "공고에 없음(상시 채용 포함)"}`;
  box.append(deadline);
  for (const [key, label] of SUMMARY_FIELDS) {
    const h = document.createElement("h3");
    h.textContent = label;
    const ul = document.createElement("ul");
    const items = Array.isArray(summary[key]) ? summary[key] : [];
    if (items.length === 0) {
      const li = document.createElement("li");
      li.textContent = "(공고에 적힌 내용 없음)";
      ul.append(li);
    }
    for (const text of items) {
      const li = document.createElement("li");
      li.textContent = text; // 모델이 <script>를 내놓아도 글자로만 보인다
      ul.append(li);
    }
    box.append(h, ul);
  }
  const note = document.createElement("p");
  note.className = "note";
  note.textContent = `AI가 만든 요약이다. 지원 전에 공고 원문을 확인한다. (${meta.fake ? "모의 모드" : meta.model}, 판본 ${meta.prompt})`;
  box.append(note);
}

async function requestSummary(text) {
  const btn = document.getElementById("summary-btn");
  const status = document.getElementById("summary-status");
  const box = document.getElementById("summary");
  btn.disabled = true;
  box.setAttribute("aria-busy", "true");
  status.className = "";
  status.textContent = "요약을 만드는 중이다(몇 초 걸린다).";
  try {
    const res = await fetch("/api/summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const reason = typeof data.detail === "string" ? data.detail : `오류 ${res.status}`;
      throw new Error(reason);
    }
    renderSummary(box, data.summary, data.meta);
    status.textContent = data.meta.cached ? "요약을 불러왔다(저장된 결과)." : "요약을 만들었다.";
  } catch (e) {
    status.className = "error";
    status.textContent = `요약을 만들지 못했다. ${e.message} 잠시 뒤 다시 누른다.`;
  } finally {
    btn.disabled = false;
    box.removeAttribute("aria-busy");
  }
}

async function setupSummary() {
  const btn = document.getElementById("summary-btn");
  if (!btn) return;
  const id = new URLSearchParams(location.search).get("id");
  let job;
  try {
    job = (await loadJobs()).find((item) => item.id === id);
  } catch (e) {
    job = undefined;
  }
  if (!job) return; // 없는 공고면 버튼을 켜지 않는다
  btn.disabled = false;
  btn.addEventListener("click", () => requestSummary(jobToText(job)));
}

setupSummary();
