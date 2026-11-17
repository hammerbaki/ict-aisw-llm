// jobprep 프로토타입의 동작. 빌드 도구 없이 브라우저에서 바로 연다.
// 화면마다 <body data-page="…">를 두고, 아래 표에서 그 화면의 초기화 함수를 부른다.
// 주소 뒤의 ?state=empty|loading|error 로 화면 명세의 상태를 보일 수 있게 한다.

const params = new URLSearchParams(location.search);
const forcedState = params.get("state");

function initJobList() {
  // SCR-01 공고 목록: 화면 명세에 따라 채운다
}

const page = document.body.dataset.page;
({ "job-list": initJobList }[page] || (() => {}))();
