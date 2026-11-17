# 3장 키트: 팀 규칙의 공유 (CLAUDE.md, 설정, 저장소 규약)

「AI에이전트 기획 및 개발」 3장(학사 4주차)의 실습 재료이다. 강의안은 `Agent_03장_학생용.md`이다.
이 장에서는 내 PC의 `~/agent-lab/jobprep/`에 팀이 함께 쓰는 규칙 파일 일체를 만들고, 규칙이 없을 때 생긴 어긋남 하나를 골라 그 규칙으로 막혔는지 확인한다.

## 받기

키트 저장소(`~/kits-repo`)에서 받는다(부록 A-7-3).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_03장 ~/kits/
```

## 들어 있는 것

| 경로 | 내용 | 어디로 가는가 |
|---|---|---|
| `ops/rules/` | 규칙 검사 도구 넷과 그 테스트. 표준 라이브러리만 쓴다 | 저장소의 `ops/rules/`로 복사한다(0-3절) |
| `ops/rules/check_commits.py` | 커밋 메시지(Conventional Commits)와 브랜치 이름 검사 | |
| `ops/rules/count_violations.py` | 변경 내역(diff)에서 팀 규칙의 위반을 세어 표로 냄 | |
| `ops/rules/lint_rules.py` | 규칙 파일 자체의 검사(CLAUDE.md 길이와 절, 경로별 규칙의 paths, settings.json, 개인 설정 제외, PR 템플릿, CODEOWNERS) | |
| `ops/rules/perm_sim.py` | 권한 규칙 판정의 학습용 모의기. Claude Code 자체의 판정기가 아니다 | |
| `githooks/commit-msg` | 커밋 메시지를 검사하는 git 훅 | 저장소의 `.githooks/`로 복사한다(8-9절) |
| `규약/` | 기준 규약 셋: `저장소규약.md`, `pull_request_template.md`, `CODEOWNERS` | 8-9절(따라 하기 3)에서 `docs/운영/`, `.github/`, 루트로 복사하고 날짜와 GitHub 아이디를 채운다 |
| `양식/` | `CLAUDE_양식.md`, `rules_api_양식.md`, `rules_tests_양식.md`, `settings_양식.json`, `규칙비교_양식.md`(핵심 실습), `저장소규약_양식.md`, `pull_request_template_양식.md`, `CODEOWNERS_양식`(규약을 처음부터 쓸 때, [선택]) | 10절(핵심 실습)에서 제자리 이름으로 복사해 채운다 |
| `견본/판정사례.txt` | 권한 판정 사례 23개(호출과 기대 판정). 10-5절의 팀 설정을 검사한다 | 10절 |
| `견본/설정/` | 사용자, 프로젝트, 로컬 세 범위의 설정 견본과 판정 사례 | 3-6절(읽기), 4-8절(따라 하기) |
| `견본/커밋메시지.txt` | 커밋 메시지 견본 9개(통과 3, 위반 6) | 8-3절(읽기) |
| `견본/비교/` | 규칙 유무 비교의 diff 견본 두 개(집필자가 만든 것. 실제 모델 출력이 아니다) | 9-4절(읽기) |
| `기준산출물/` | 2장 결과의 견본: 미구현 요구 셋(REQ-JOB-06, REQ-SUM-05, REQ-ASK-06)의 구현과 테스트 | 2장을 마치지 못한 학습자만 0-2절에서 쓴다 |
| `시연기록/` | 규칙 유무 비교의 교수 시연 기록(묶음 둘, 대화 기록, 조건). 교수가 수업 전에 키트 저장소에 올린다 | 10-2절에서 `git clone`으로 받는다 |
| `교수/` | 완성본과 시연 안내(교수용) | 키트 저장소에 올리지 않는다(학생 키트에는 없다) |

규칙 파일의 양식은 일부러 `CLAUDE.md`, `.claude/rules/` 같은 제자리 이름을 쓰지 않았다. 키트 폴더 안에서 Claude Code를 실행해도 양식이 규칙으로 읽히지 않게 하기 위해서이다.

## 쓰는 순서

1. 0절: 키트 받기, 2장 결과 확인(없으면 `기준산출물/` 적용), 작업 브랜치 `chore/team-rules` 만들기, `ops/rules/` 복사
2. 1~9절: 이론. 따라 하기는 셋이다(4-8 권한 규칙 판독은 `견본/설정/`, 7-3 개인 파일의 제외, 8-9 `규약/`과 `githooks/`로 저장소 규약과 커밋 훅). 3-6, 8-3, 9-4는 `견본/`의 출력을 읽는다
3. 10절(핵심 실습): 교수 시연 기록(`시연기록/`)의 「규칙 없음」에서 막을 어긋남 하나를 고르고, `양식/`을 복사해 그것을 막는 지시와 설정(`CLAUDE.md`, 경로별 규칙, `settings.json`)을 만들고, `lint_rules.py`와 판정 사례로 검사한 뒤, 같은 요청 하나를 자기 규칙에서 다시 보내 그 어긋남이 막혔는지 `docs/운영/규칙비교.md`에 기록한다

## 도구의 테스트

```bash
cd ~/agent-lab/jobprep
source .venv/Scripts/activate      # macOS: source .venv/bin/activate
python -m pytest -q ops/rules/tests
```

기본 `pytest -q`는 `pytest.ini`의 `testpaths = tests`만 돌므로 도구의 테스트는 위처럼 경로를 주어 돌린다. 키트 폴더에서 돌리면 견본 파일을 쓰는 테스트가 더 검사한다(판정 사례의 검사는 `교수/`가 있는 교수 사본에서만 돌고, 학생 키트에서는 건너뛴다).

## 확인한 환경

- 2026-11-14: Windows 11의 Git Bash, Python 3.13.7, git 2.55, Claude Code 2.1.296에서 도구의 테스트 80개가 통과하였다(정합 작업에서 브랜치 종류 `agent`, `loop`, `practice`와 그 테스트를 더한 뒤 90개).
- 2026-11-17(결정 11, 내 PC 기준): 같은 PC에서 가상 환경을 켠 `python`으로 학생 키트(`교수/` 제외)와 교수 사본 두 경우의 `python -m pytest -q ops/rules/tests`를 돌렸다. 결과는 강의안 교수용 「확인한 것」에 있다. macOS는 확인하지 못하였다.
