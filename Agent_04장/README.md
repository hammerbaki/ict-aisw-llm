# Agent_04장 키트: 확장 기능의 구조 (커맨드, 스킬, 플러그인)

「AI에이전트 기획 및 개발」 4장의 실습 재료이다. 핵심 실습(9절)은 반복 운영 작업 하나(운영 기록으로 장애 보고서 쓰기)를 커맨드 → 스킬 → 플러그인으로 키우고, 팀 마켓플레이스로 다른 폴더에 설치하는 한 흐름이다. 해결하는 문제는 「커맨드가 쓴 보고서가 팀 서식 검사를 통과하지 못한다」이다. 작업은 내 PC의 저장소 `~/agent-lab/jobprep/`에서 한다. 받는 법은 강의안 0절과 부록 A-7을 따른다.

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_04장 ~/kits/
```

## 들어 있는 것

| 경로 | 쓰는 절 | 내용 |
|---|---|---|
| `기준산출물/` | 0절 | 3장 결과의 규칙 파일. 3장 키트의 교수 완성본(팀 `CLAUDE.md`, `.claude/rules/api.md`·`tests.md`, `.claude/settings.json`)을 제자리 이름으로 옮겼다. 3장을 마친 학습자는 쓰지 않는다 |
| `재료/incident-report/references/` | 9-4(2단계) | 보고서 서식, 심각도 기준. 스킬 폴더에 복사한다 |
| `재료/incident-report/scripts/` | 4-6(따라 하기 2), 9-3, 9-4 | `log_summary.py`(하루치 기록 요약), `check_report.py`(보고서 서식 검사). 표준 라이브러리만 쓴다 |
| `tests/test_ops_skill.py` | 9-4(2단계) | 스크립트 동작과 SKILL.md 형식 테스트. 저장소 `tests/`에 복사한다 |
| `tests/test_ops_plugin.py` | 9-6(3단계) | 플러그인 매니페스트와 마켓플레이스 구조 테스트 |
| `antipattern/` | 5절(읽기) | 스킬 안티패턴 샘플 셋과 진단 기준(2026년 2학기판 재료) |
| `스킬비교_양식.md` | 9-5, 10절 | `docs/운영/스킬비교.md`의 양식 |
| `시연기록/` | 10절 | 교수 시연(스킬 유무 비교의 반복 실행)의 기록을 받는 자리. 교수가 기록을 올리기 전에는 집필 예시 `A_집필예시.md`와 안내만 있다 |
| `예비/` | 막힐 때 | 각 단계의 완성본: 커맨드(`incident-report.md`), 스킬(`SKILL.md`), `plugin.json`, `marketplace.json`, 플러그인 README |
| `교수/` | 교수 | 시연 지시, 비교 실행 스크립트(`시연_비교실행.sh`), 비교용 예시 보고서 셋, 비교 판정 예. 학생 키트(키트 저장소)와 공개 목록에 넣지 않는다 |

## 단계와 저장소에 남는 것

명령은 가상 환경을 켠 터미널에서 실행한다(Windows Git Bash `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`). 그 뒤로는 운영체제와 관계없이 `python`, `python -m pytest`이다.

| 단계 | 저장소의 파일 | 확인 명령 |
|---|---|---|
| 1. 커맨드 | `.claude/commands/incident-report.md` | `claude plugin validate .claude` |
| 2. 스킬 | `.claude/skills/incident-report/` (SKILL.md, references/, scripts/), `tests/test_ops_skill.py` | `python -m pytest`, `claude plugin validate .claude` |
| 3. 플러그인 | `plugins/jobprep-ops/`, `.claude-plugin/marketplace.json`, `tests/test_ops_plugin.py` | `python -m pytest`, `claude plugin validate ./plugins/jobprep-ops --strict`, `claude plugin validate .` |
| 비교 | `docs/운영/스킬비교.md`, `docs/운영/장애보고/` | `python <스킬 폴더>/scripts/check_report.py <보고서>` |

2단계에서 커맨드 파일을 스킬 폴더로 옮기고(`git mv`), 3단계에서 스킬 폴더를 플러그인 안으로 옮긴다. 같은 이름의 스킬이 두 곳에 남지 않게 하기 위해서이다.

스킬의 `allowed-tools`와 본문은 `python`으로 스크립트를 부른다. Windows의 Git Bash에는 `python3`이 없기 때문이다. 스크립트는 표준 라이브러리만 쓰므로, 가상 환경이 없는 다른 폴더(`~/agent-lab/ops-demo`)에서도 PC의 파이썬(3.12 이상)으로 돈다. Windows에서 스크립트의 한글 출력을 파이프로 넘길 때는 부록 A-4-4의 `PYTHONUTF8=1`을 등록해 둔다.

## 확인한 환경

2026-11-17, Windows 11의 Git Bash, Python 3.13.7, Claude Code 2.1.296에서 기준 저장소 사본에 세 단계를 적용해 확인하였다(`CLAUDE_CONFIG_DIR`로 격리). `python -m pytest`는 1단계 43개, 2단계 61개, 3단계 65개가 통과한다. 키트의 테스트는 `교수/` 폴더를 읽지 않으므로 학생 키트에서도 같은 결과이다. macOS에서는 실행하지 못하였다.
