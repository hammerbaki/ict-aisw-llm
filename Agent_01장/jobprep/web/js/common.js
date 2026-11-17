// 여러 화면이 함께 쓰는 함수: API 주소, API 호출, 관심 공고 저장.

// API 서버 주소. 이 과목은 내 PC에서 API 8000, 웹 8100의 고정 포트로 띄운다(부록 A-10).
// 웹을 8100(또는 8101~8199 밖의 포트)에서 열면 같은 호스트의 8000번 API를 부른다.
// 8000번을 다른 프로그램이 쓰고 있어 API를 다른 번호로 띄웠으면, 주소 끝에 ?api=8001 처럼 적거나
// 웹을 그보다 100 큰 포트(예: 웹 8101 → API 8001)에서 연다.
const API_BASE = (() => {
  const host = location.hostname || "127.0.0.1";
  const given = new URLSearchParams(location.search).get("api");
  if (given && /^\d+$/.test(given)) return `http://${host}:${given}`;
  const port = Number(location.port);
  if (port >= 8101 && port <= 8199) return `http://${host}:${port - 100}`;
  return `http://${host}:8000`;
})();
const FAVORITES_KEY = "jobprep.favorites";

// API를 부르고 JSON을 돌려준다. 실패하면 서버가 보낸 detail을 담은 오류를 낸다.
async function callApi(path, options = {}) {
  const response = await fetch(API_BASE + path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `상태 코드 ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

function postJson(path, data) {
  return callApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// 관심 공고는 브라우저의 localStorage에 공고 id 목록으로 저장한다.
function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY)) || [];
  } catch {
    return [];
  }
}

function isFavorite(id) {
  return loadFavorites().includes(id);
}

// 관심 공고에 없으면 넣고, 있으면 뺀다. 바뀐 뒤의 상태(true: 관심)를 돌려준다.
function toggleFavorite(id) {
  let favorites = loadFavorites();
  if (favorites.includes(id)) {
    favorites = favorites.filter((x) => x !== id);
  } else {
    favorites.push(id);
  }
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
  return favorites.includes(id);
}

// 태그와 글을 받아 요소를 만든다. 글은 textContent로 넣어 HTML로 해석되지 않게 한다.
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function showStatus(target, message, isError = false) {
  target.textContent = message;
  target.classList.toggle("error", isError);
}

// 마감까지 남은 날 수를 "D-7", "오늘 마감", "마감"으로 나타낸다.
function dDay(daysLeft) {
  if (daysLeft < 0) return "마감";
  if (daysLeft === 0) return "오늘 마감";
  return `D-${daysLeft}`;
}
