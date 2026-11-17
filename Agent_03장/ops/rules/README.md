# ops/rules: 팀 규칙 검사 도구

3장에서 만든 팀 규칙(`CLAUDE.md`, `.claude/`, `docs/운영/저장소규약.md`, `.github/pull_request_template.md`, `CODEOWNERS`)을 기계로 확인하는 도구이다. 파이썬 표준 라이브러리만 쓴다. 명령은 저장소 폴더에서, 가상 환경을 켠 터미널에서 실행한다(Windows Git Bash `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`).

| 명령 | 하는 일 |
|---|---|
| `python ops/rules/lint_rules.py` | 규칙 파일 자체를 검사한다. 실패가 있으면 종료 코드 1 |
| `python ops/rules/check_commits.py --range main..HEAD` | 범위 안 커밋 메시지(병합 커밋 제외)를 검사한다 |
| `python ops/rules/check_commits.py --branch` | 지금 브랜치의 이름을 검사한다 |
| `python ops/rules/count_violations.py --base rules-v1` | 시작점부터 HEAD까지의 변경에서 규칙 위반을 센다 |
| `python ops/rules/perm_sim.py "Bash(git push origin main)" --settings .claude/settings.json` | 권한 규칙의 판정을 흉내 낸다(학습용 모의기) |
| `python -m pytest -q ops/rules/tests` | 이 도구들의 테스트 |

- 규칙의 문장을 바꾸면 검사도 함께 고친다. `check_commits.py`의 `TYPES`, `count_violations.py`의 `CHECKS`, `lint_rules.py`의 `REQUIRED_SECTIONS`가 규칙과 짝이다.
- `perm_sim.py`는 Claude Code 문서의 판정 규칙 일부를 옮긴 모의기이다. 실제 판정은 Claude Code 안의 `/permissions`와 실행 결과로 확인한다.
- 13장에서 이 도구들을 지속적 통합(CI)의 검사로 쓴다.
