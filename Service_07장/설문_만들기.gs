// Google Apps Script. script.google.com 의 새 프로젝트에 붙여 넣고 createSurvey 를 실행한다.
// 2026-11-18 기준 실행으로 확인하지 않았다. 수업 전에 교수가 실행해 확인한다.
function createSurvey() {
  const form = FormApp.create('실습실 자리 잡기 설문 (2분)');
  form.setDescription('졸업 프로젝트 조가 실습실 예약 서비스를 고치려고 묻습니다. '
    + '이름, 학번, 연락처는 받지 않습니다.');
  form.setCollectEmail(false);

  form.addMultipleChoiceItem()
    .setTitle('지난 한 달에 학과 실습실을 몇 번 썼습니까?')
    .setChoiceValues(['없음', '1~2번', '3~5번', '6번 이상'])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('그때 자리를 어떻게 잡았습니까? (모두 고르기)')
    .setChoiceValues(['예약 앱', '그냥 가서 앉음', '단체방에서 물어봄', '기타']);

  form.addMultipleChoiceItem()
    .setTitle('예약해 두고 쓰지 않은 적이 있습니까?')
    .setChoiceValues(['없음', '한 번', '여러 번', '예약한 적 없음']);

  form.addParagraphTextItem()
    .setTitle('실습실 자리를 잡다가 가장 최근에 곤란했던 일을 한 가지 적어 주세요. (선택)');

  Logger.log('응답 주소: ' + form.getPublishedUrl());
  Logger.log('편집 주소: ' + form.getEditUrl());
}
