---
paths:
  - "web/**"
---

# 웹 코드 규칙

- 화면에 글을 넣을 때는 `textContent` 또는 `js/common.js`의 `el()`만 쓴다. `innerHTML`을 쓰지 않는다.
- API 주소는 `js/common.js`의 `API_BASE`만 쓴다. 다른 파일에 주소를 적지 않는다.
- 빌드 도구와 외부 라이브러리를 더하지 않는다.
