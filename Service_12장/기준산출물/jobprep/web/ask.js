// 취업 자료 질의응답 화면. POST /api/ask를 부르고 답과 근거를 보인다.
// 원칙: 서버가 준 글(답, 근거 본문)은 모두 textContent로 넣는다. HTML 문자열로 넣는 속성은 쓰지 않는다.
// 답과 근거에는 자료 작성자나 모델이 만든 글이 섞여 있으므로 HTML로 해석하면 스크립트가 실행될 수 있다.

const API_BASE = window.JOBPREP_API_BASE || "";  // 같은 서버에서 열면 비워 둔다
const MAX_TURNS = 4;                              // 서버로 보낼 최근 왕복 수(서버도 다시 자른다)
let history = [];                                 // 원래 질문과 답만 담는다

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  $("status").textContent = text;
}

// 답 문자열의 [1], [2]를 근거 목록으로 가는 링크로 바꾼다. 나머지는 글자 그대로 둔다.
function renderAnswer(text, citationCount) {
  const box = $("answer");
  box.replaceChildren();
  const parts = text.split(/(\[\d+\])/);
  for (const part of parts) {
    const m = part.match(/^\[(\d+)\]$/);
    const n = m ? Number(m[1]) : 0;
    if (m && n >= 1 && n <= citationCount) {
      const a = document.createElement("a");
      a.href = `#cite-${n}`;
      a.textContent = part;
      a.className = "cite";
      box.append(a);
    } else {
      box.append(document.createTextNode(part));
    }
  }
}

function renderCitations(citations) {
  const list = $("citations");
  list.replaceChildren();
  for (const c of citations) {
    const li = document.createElement("li");
    li.id = `cite-${c.n}`;
    if (c.cited) li.className = "cited";
    const head = document.createElement("div");
    head.className = "cite-head";
    head.textContent = `[${c.n}] ${c.title} › ${c.heading}  (유사도 ${c.score.toFixed(3)}${c.cited ? ", 답에 사용" : ""})`;
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "근거 본문 보기";
    const body = document.createElement("p");
    body.textContent = c.excerpt;
    details.append(summary, body);
    li.append(head, details);
    list.append(li);
  }
}

function addLog(question) {
  const li = document.createElement("li");
  li.textContent = question;
  $("log").append(li);
  $("log-section").hidden = false;
}

async function ask(question) {
  const response = await fetch(`${API_BASE}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history: history.slice(-MAX_TURNS * 2) }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(`${response.status} ${JSON.stringify(detail.detail ?? "")}`);
  }
  return response.json();
}

$("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) return;
  $("send").disabled = true;
  setStatus("자료를 찾는 중이다…");
  try {
    const data = await ask(question);
    renderAnswer(data.answer, data.citations.length);
    renderCitations(data.citations);
    $("grounding").textContent = data.grounded
      ? `근거 ${data.citations.length}개를 찾아 답하였다(1위 유사도 ${data.top_score.toFixed(3)}).`
      : `자료에서 충분히 가까운 근거를 찾지 못하였다(1위 유사도 ${data.top_score.toFixed(3)}).`;
    $("result").hidden = false;
    history.push({ role: "user", content: question }, { role: "assistant", content: data.answer });
    addLog(question);
    setStatus("");
    $("question").value = "";
  } catch (err) {
    setStatus(`요청이 실패하였다: ${err.message}`);
  } finally {
    $("send").disabled = false;
  }
});

$("reset").addEventListener("click", () => {
  history = [];
  $("log").replaceChildren();
  $("log-section").hidden = true;
  $("result").hidden = true;
  setStatus("대화를 새로 시작한다.");
});
