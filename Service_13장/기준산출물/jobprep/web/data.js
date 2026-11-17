// 13장 평가용 견본의 자료. 모든 회사와 공고는 가상이다.
// 날짜는 페이지를 연 날을 기준으로 정한다(dueIn: 마감까지 남은 날, postedAgo: 등록한 지 지난 날).
const JOBS = [
  {
    id: "J-2027-0412", company: "가온소프트", title: "백엔드 개발(신입)", region: "서울",
    dueIn: 4, postedAgo: 19, views: 1842, manager: "HR-07",
    body: "Python 또는 Java로 웹 API를 개발한 경험이 있는 분을 찾는다. 자격: 전문대학 이상 졸업(예정)자. " +
          "우대: FastAPI 사용 경험, Git으로 협업한 경험. 근무: 서울 구로구, 주 5일. 전형: 서류, 코딩 테스트, 면접."
  },
  {
    id: "J-2027-0415", company: "누리데이터", title: "데이터 분석 보조", region: "경기",
    dueIn: 11, postedAgo: 17, views: 920, manager: "HR-02",
    body: "사내 판매 자료를 정리하고 보고서를 만든다. 자격: SQL 기초, 엑셀 피벗. " +
          "우대: 파이썬 pandas 사용 경험. 근무: 경기 성남시. 전형: 서류, 면접."
  },
  {
    id: "J-2027-0420", company: "다솜웹", title: "프런트엔드 개발(인턴)", region: "서울",
    dueIn: 25, postedAgo: 15, views: 2310, manager: "HR-11",
    body: "HTML, CSS, 자바스크립트로 화면을 만든다. 자격: 포트폴리오 제출 필수. " +
          "우대: 접근성(WCAG) 이해. 근무: 서울 마포구, 6개월 인턴 뒤 정규직 전환 심사."
  },
  {
    id: "J-2027-0423", company: "라온클라우드", title: "백엔드 개발(신입)", region: "대전",
    dueIn: 6, postedAgo: 13, views: 640, manager: "HR-03",
    body: "클라우드 서비스의 API를 개발하고 운영한다. 자격: 리눅스 명령어 사용 가능. " +
          "우대: Docker 사용 경험. 근무: 대전 유성구. 전형: 서류, 과제, 면접."
  },
  {
    id: "J-2027-0431", company: "마루AI", title: "AI 서비스 개발(신입)", region: "서울",
    dueIn: 15, postedAgo: 10, views: 3105, manager: "HR-01",
    body: "LLM API를 사용한 사내 도구를 개발한다. 자격: 파이썬 프로그래밍. " +
          "우대: RAG 구현 경험, 프롬프트 평가 경험. 근무: 서울 강남구. 전형: 서류, 코딩 테스트, 면접."
  },
  {
    id: "J-2027-0433", company: "바다시스템", title: "QA 엔지니어(신입)", region: "경기",
    dueIn: 18, postedAgo: 9, views: 412, manager: "HR-05",
    body: ""
  }
];

// 학과 취업 자료(가상). 자료 묻기가 근거로 삼는 문서다.
const GUIDES = [
  { title: "취업 상담 신청 안내", keywords: ["상담", "신청"],
    text: "취업 상담은 학과 사무실 앞 신청서 또는 학과 누리집의 상담 신청 메뉴로 신청한다. 상담은 화요일과 목요일 오후에 한다." },
  { title: "포트폴리오 작성 안내", keywords: ["포트폴리오"],
    text: "포트폴리오는 PDF 한 파일로 만들고, 프로젝트마다 맡은 역할과 저장소 주소를 적는다." },
  { title: "이력서 첨삭 안내", keywords: ["이력서", "첨삭"],
    text: "이력서 첨삭은 마감 7일 전까지 신청해야 한다. 첨삭 결과는 3일 안에 메일로 받는다." }
];

// 날짜를 연 날 기준으로 채운다.
(function fillDates() {
  const iso = (d) => d.toISOString().slice(0, 10);
  const today = new Date();
  JOBS.forEach((j) => {
    j.due = iso(new Date(today.getTime() + j.dueIn * 86400000));
    j.posted = iso(new Date(today.getTime() - j.postedAgo * 86400000));
  });
})();
