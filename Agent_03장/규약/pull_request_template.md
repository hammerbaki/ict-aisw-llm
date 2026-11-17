## 무엇을 바꾸었는가

<!-- 한두 문장. 관련 요구가 있으면 REQ-ID를 적는다. 예: REQ-JOB-06 마감 임박 필터를 더한다 -->

## 왜 바꾸었는가

<!-- 이 변경이 필요한 까닭. 이슈가 있으면 Closes #번호 -->

## 어떻게 확인하였는가

- [ ] `python -m pytest -q` 통과 (결과 줄: )
- [ ] `python ops/rules/lint_rules.py` 실패 0건
- [ ] `python ops/rules/check_commits.py --range main..HEAD` 위반 0건
- [ ] 화면이 바뀌었으면 브라우저에서 직접 확인하였다(해당 없으면 지운다)

## 에이전트 사용

- [ ] 이 PR에 Claude Code가 만든 변경이 있다. 있으면 사람이 diff를 모두 읽었다
- 사용한 요청(요약):

## 규칙 파일 변경

<!-- CLAUDE.md, .claude/, .github/, CODEOWNERS, docs/운영/저장소규약.md를 바꾸었으면 무엇을 왜 바꾸었는지 적는다. 없으면 "없음" -->

## 검토자에게

<!-- 특히 봐 주었으면 하는 곳 -->
