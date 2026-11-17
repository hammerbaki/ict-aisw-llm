// 취업 자료 질의응답 화면: 질문을 보내고 답과 근거를 보여 준다.

const statusBox = document.getElementById("status");
const questionBox = document.getElementById("question");
const askButton = document.getElementById("ask-button");

function renderSources(sources) {
  const list = document.getElementById("sources");
  if (!sources.length) {
    list.replaceChildren(el("li", "(인용한 근거 없음)"));
    return;
  }
  list.replaceChildren(...sources.map((s) => el("li", `[${s.no}] ${s.title} (${s.source}, 유사도 ${s.score})`)));
}

document.getElementById("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionBox.value.trim();
  if (!question) return;

  askButton.disabled = true;
  showStatus(statusBox, "자료를 찾아 답을 만드는 중이다.");
  try {
    const result = await postJson("/api/ask", { question });
    document.getElementById("answer").textContent = result.answer;
    renderSources(result.sources);
    document.getElementById("answer-meta").textContent =
      `프롬프트 ${result.prompt_version} · 모델 ${result.model || "(부르지 않음)"}`;
    document.getElementById("result").hidden = false;
    showStatus(statusBox, "");
  } catch (error) {
    showStatus(statusBox, `답하지 못하였다: ${error.message}`, true);
  } finally {
    askButton.disabled = false;
  }
});
