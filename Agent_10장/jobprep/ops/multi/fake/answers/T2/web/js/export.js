// 관심 공고 내보내기 (REQ-FAV-05): 관심 공고 번호로 내보내기 API의 주소를 만들어 CSV를 내려받는다.
// common.js(API_BASE, loadFavorites, el, showStatus)와 list.js(statusBox) 다음에 불러온다.

const exportButton = document.getElementById("export-favorites");

// 계획서의 계약: GET /api/favorites/export?ids=3,1
function exportUrl(ids) {
  const params = new URLSearchParams({ ids: ids.join(",") });
  return `${API_BASE}/api/favorites/export?${params}`;
}

exportButton.addEventListener("click", () => {
  const ids = loadFavorites();
  if (ids.length === 0) {
    showStatus(statusBox, "내보낼 관심 공고가 없다. 목록에서 별표로 관심 공고를 먼저 표시한다.", true);
    return;
  }
  // API가 보내는 Content-Disposition: attachment 머리글 때문에 화면을 떠나지 않고 파일이 내려받아진다.
  const link = el("a");
  link.href = exportUrl(ids);
  link.download = "favorites.csv";
  document.body.append(link);
  link.click();
  link.remove();
  showStatus(statusBox, `관심 공고 ${ids.length}건을 내보냈다.`);
});
