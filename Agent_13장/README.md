# Agent_13장 키트: 지속적 통합과 안정적 배포

「AI에이전트 기획 및 개발」 13장(학사 15주차)의 실습 재료이다. 강의안 `Agent_13장_학생용.md`의 절 번호를 따라 쓴다.

## 받기

키트 저장소에서 저장소 밖의 `~/kits/`로 받는다(부록 A-7-3).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_13장 ~/kits/
```

키트는 저장소 밖(`~/kits/`)에 두고, 단계마다 필요한 파일만 `~/agent-lab/jobprep/`으로 복사한다. 이 장의 배포 대상은 사용자 결정 11(Q6)에 따라 정적 웹은 GitHub Pages, API는 GitHub 릴리스까지이다. 실습 서버에 배포하지 않는다.

## 구성

| 경로 | 절 | 저장소로 옮기는 곳 | 내용 |
|---|---|---|---|
| `기준산출물/` | 0 | 같은 경로 | 앞 장을 마치지 못한 학습자용 견본. 2장(테스트 `tests/test_closing_within.py`, `tests/test_input_limits.py`와 구현 `api/jobs.py`, `api/main.py`, 명세서), 3장(`ops/rules/check_code_rules.py`), 11장(11장 키트의 `security/scan_secrets.py`와 `security/tools/`, 종류 이름을 11장에 맞춘 `security/allowlist.txt`), 12장(`evals/run_evals.py`, `evals/golden.jsonl`, `evals/regression_baseline.json`. 12장을 마친 학습자는 쓰지 않는다) |
| `ops/ci/eval_gate.sh` | 0, 6 | `ops/ci/` | CI의 `eval` 작업이 부르는 입구. `evals/gate.py`가 있으면 12장의 `evals.run`과 `evals.gate`를(판본은 `.env.example`의 `PROMPT_*`), 없으면 견본 `run_evals.py --check`를 돌린다 |
| `ci/ci.yml` | 2, 6 | `.github/workflows/` | CI 워크플로(작업 `test`, `eval`, `secrets`, `rules`. PR과 `main`·`agent/*`·`loop/*` 푸시). API 키 없이 통과. 모든 작업이 `.python-version`의 파이썬을 쓴다 |
| `ops/version/check_pins.py` | 3, 6 | `ops/version/` | 버전 고정 검사(P1 액션 SHA, P2 잠금 파일, P3 파이썬 판, P4 모델 이름, P5 프롬프트 판본) |
| `ops/ci/local_ci.sh` | 6 | `ops/ci/` | CI의 네 작업이 부르는 명령을 같은 순서로 내 PC에서 실행. `--fresh`는 새 가상 환경에 잠금 파일로 설치한 뒤 실행 |
| `ops/protect/` | 6 | `ops/protect/` | 규칙 집합(`ruleset.json`), 에이전트·루프 브랜치의 강제 푸시 금지(`ruleset_agent.json`), 예전 방식 보호 규칙(`branch_protection.json`)의 요청 본문, `set_protection.sh`(`show`, `ruleset`, `agent`, `classic`) |
| `ci/release.yml` | 5, 6 | `.github/workflows/` | 태그 `v*.*.*` 푸시 때 CI를 다시 돌리고 GitHub 릴리스를 만든다(API는 릴리스까지) |
| `ci/pages.yml` | 5, 6 | `.github/workflows/` | 사람이 고른 태그의 `web/`을 Pages에 배포한다(`gh workflow run pages.yml -f tag=v1.0.0`). 배포 전에 `ci_passed.sh`로 그 태그가 CI를 통과했는지 묻고, `version.txt`에 판과 커밋을 적는다. 되돌리기는 직전 판의 태그로 같은 명령 |
| `ops/release/notes.py` | 6 | `ops/release/` | `CHANGELOG.md`에서 판 하나의 절을 뽑는다 |
| `ops/release/ci_passed.sh` | 6 | `ops/release/` | 태그 커밋의 `test`, `eval`, `secrets`, `rules`가 모두 success인지 GitHub에 묻는다 |
| `연습/test_jobs_search_case.py` | 6 | `tests/` | 검색어 대소문자 무시의 테스트(수정 전 2개 실패) |
| `연습/문제변경.patch` | 6 | `git apply`로 적용 | 질의응답 기준값을 0.3에서 0.35로 올리는 「문제 있는 변경」. 테스트는 통과하고 회귀 평가가 실패한다 |
| `ops/map/check_map.py` | 7 | `ops/map/` | 운영 요건 지도의 경로, 칸, 1장 요건 ID(`OR-…`) 검사 |
| `CHANGELOG_양식.md` | 6 | `CHANGELOG.md` | Keep a Changelog 1.1.0 형식 |
| `배포점검표_양식.md` | 6 | `docs/운영/배포점검표.md` | 점검 목록(배포 전, 릴리스와 배포, 배포 뒤)과 배포 기록 |
| `보호규칙기록_양식.md` | 6 | 배포 점검표의 3절로 붙인다 | 보호 규칙 설정 기록 |
| `운영요건지도_양식.md` | 7 | `docs/운영/운영요건지도.md` | 요건, 장, 산출물, 확인 방법, 자동화, 남은 위험 |
| `tests/test_kit.py` | 확인용 | 옮기지 않는다 | 키트 도구와 워크플로의 테스트 |

pip-tools와 actionlint는 저장소 밖 `~/agent-lab/.tools/`에 둔다(부록 A-19). Windows는 actionlint의 Windows 판(`actionlint.exe`)을 쓴다.

## 키트 도구의 테스트

```bash
cd ~/kits/Agent_13장
python -m pytest -q -p no:cacheprovider tests
```

pytest가 있는 가상 환경을 켠 터미널에서 실행한다(`jobprep`의 가상 환경을 켜면 된다). 2026-11-17에 Windows 11의 Git Bash에서 19개가 통과하였다.

## 기대하는 실패 화면

6절의 「문제 있는 변경」을 적용하면 `python -m pytest -q`는 통과하고, `bash ops/ci/eval_gate.sh`는 종료 코드 1로 끝나야 한다. 견본 평가의 출력은 다음과 같다. 12장의 판정기를 쓰면 `[실패] ask 기준선 대비 -0.19`와 `결과: 회귀(종료 코드 1)`가 나온다.

```text
실패  ask-04       근거를 찾지 못함(자료에 없습니다.)
실패  ask-10       근거를 찾지 못함(자료에 없습니다.)
합계: 16/18 통과 (model=fake, summary=summary_v1, ask=ask_v1)
회귀: 기준에서 통과하던 문항이 실패: ask-04, ask-10
회귀: 통과율 하락: 1.00 -> 0.89
```

## 판과 날짜

- 액션의 SHA는 `gh api repos/<소유자>/<저장소>/commits/<태그>`로 확인하였다(2026-11-14, 2026-11-17): `actions/checkout` v7.0.1, `actions/setup-python` v7.1.0, `actions/configure-pages` v6.0.0, `actions/upload-pages-artifact` v5.0.0, `actions/deploy-pages` v5.0.1, `anthropics/claude-code-action` v1.0.276(교수 시연용). 수업 전에 새 판을 확인한다.
- 잠금 파일 도구: pip-tools 7.6.2(2026-11-16에 7.7.0이 나왔다. 부록 A-19가 정한 판을 쓴다). 문법 검사: actionlint 1.7.12.
- 서버 배포 스크립트(`deploy.sh`, `rollback.sh`, `status.sh`)는 결정 11(Q6)로 학생 키트에서 빼고 `교수/참고_서버배포/`에 두었다.
