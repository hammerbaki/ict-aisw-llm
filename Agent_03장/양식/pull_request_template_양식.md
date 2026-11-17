## 무엇을 바꾸었는가

<!-- 한두 문장. 관련 요구가 있으면 REQ-ID를 적는다 -->

## 왜 바꾸었는가

<!-- 이 변경이 필요한 까닭 -->

## 어떻게 확인하였는가

- [ ] `python -m pytest -q` 통과 (결과 줄: )
- [ ] `python ops/rules/lint_rules.py` 실패 0건
- [ ] `python ops/rules/check_commits.py --range main..HEAD` 위반 0건
- [ ] 「화면 확인 등, 팀이 더할 항목」

## 에이전트 사용

- [ ] 이 PR에 Claude Code가 만든 변경이 있다. 있으면 사람이 diff를 모두 읽었다
- 사용한 요청(요약):

## 규칙 파일 변경

<!-- CLAUDE.md, .claude/, .github/, CODEOWNERS, 저장소 규약을 바꾸었으면 무엇을 왜 바꾸었는지 적는다. 없으면 "없음" -->

## 검토자에게

<!-- 특히 봐 주었으면 하는 곳 -->
