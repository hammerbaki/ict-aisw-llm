# Agent_08장 키트: 루프 엔지니어링과 자동화

「AI에이전트 기획 및 개발」 8장(학사 10주차)의 실습 키트이다. 내 PC의 Git Bash(macOS는 터미널)에서 키트 저장소로 받아 쓰고(부록 A-7-3), `jobprep/` 안의 파일을 자기 저장소 `~/agent-lab/jobprep/`에 합친다.

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits && cp -rn ~/kits-repo/Agent_08장 ~/kits/
```

## 구성

| 경로 | 내용 | 강의안의 절 |
|---|---|---|
| `jobprep/ops/loop/fix_until_green.py` | 루프 스크립트. 보호 경로 검사(`protected_changes`)만 비어 있다(TODO, 6-7에서 채운다) | 4, 5, 6 |
| `jobprep/ops/loop/prompt_fix.md` | 시도마다 채워 넘기는 지시문 틀 | 4, 6 |
| `jobprep/ops/loop/fake_agent.py` | `claude -p` 자리에 끼우는 가짜 에이전트 | 2, 6, 7 |
| `jobprep/ops/loop/fake/` | 시나리오 다섯: `success`, `fail`, `budget`, `cheat`, `digest` | 6, 7 |
| `jobprep/ops/loop/digest.sh` | 수집 → 요약 → 통지 파이프라인([선택]) | 7, 8 |
| `jobprep/ops/loop/tests/test_loop.py` | 루프의 테스트 23개(작은 임시 저장소에서 루프를 실제로 돌린다) | 0, 6 |
| `jobprep/ops/loop/README.md` | 저장소 안 안내 | |
| `jobprep/docs/운영/루프설계서_양식.md` | 루프 설계서 양식 | 6 |
| `실습재료/회귀두건.patch` | `api/jobs.py`에 회귀 두 건을 심는 패치 | 6 |
| `실습재료/회귀심기.py` | 패치가 적용되지 않을 때 쓰는 같은 내용의 스크립트 | 6 |
| `실습재료/시연기록/` | 교수가 실제 `claude -p`로 돌린 기록을 키트 저장소에 올려 두는 곳. 처음에는 `README.md`만 있다. 학생이 자기 계정으로 6-9를 돌리지 못했을 때 읽는다 | 2-8, 6-9, 7-3 |
| `기준산출물/jobprep/` | 7장에서 조립한 하네스의 사본: `CLAUDE.md`, `.claude/settings.json`(권한과 훅 셋), `.claude/hooks/`(`protect.sh`, `run_tests.sh`, `stop_gate.sh`), `.claude/agents/reviewer.md`(RV1~RV8), MCP 서버, 플러그인, 동결 기록, `docs/운영/하네스설계서.md`. 출처는 `기준산출물/README.md`. 7장을 마치지 못한 학습자만 쓴다 | 0 |
| `교수/` | 교수 전용(정답본, 설계서 예시, 시연 안내, 시연 기록을 묶는 스크립트). 학생에게 배포하지 않는다 | |

## 순서

1. 키트 받기와 합치기, 테스트 두 묶음(강의안 0절). 루프 테스트는 처음에 **1 failed, 22 passed**가 정상이다. 실패하는 것은 `test_cheat_attempt_is_rejected` 하나이며, 6-7에서 `protected_changes()`를 채우면 23 passed가 된다.
2. 가짜 에이전트로 헤드리스 실행의 결과 객체를 읽는다(2-5, 따라 하기).
3. 핵심 실습(6절): 회귀를 심은 연습 브랜치에서 가짜 에이전트로 네 경로를 돌리고, 테스트 회피(`cheat`)를 보호 경로 검사로 막은 뒤, 자기 계정의 실제 에이전트로 루프를 한 번(시도 상한 3) 돌린다. `docs/운영/루프설계서.md`를 쓴다.
4. 파이프라인(7절)과 GitHub Actions(10절)는 [선택], 예약 실행(8절의 cron)은 교수 시연이다.

## 전제

- 파이썬 3.12 이상, 기준 저장소의 `requirements.txt`(pytest 9.2.0 포함). 새로 설치할 패키지는 없다. 터미널마다 가상 환경을 켜고(Windows `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`) `python`으로 부른다.
- `fix_until_green.py`와 `fake_agent.py`는 표준 라이브러리만 쓴다. 루프는 에이전트를 부를 때 가상 환경의 폴더를 `PATH` 맨 앞에 넣고 `PYTHONUTF8=1`을 준다.
- `digest.sh`는 bash와 파이썬이 필요하다(`python`, 없으면 `python3`. 환경 변수 `PYTHON`으로 바꿀 수 있다).
- Windows에서 한글이 깨지면 부록 A-4-4의 `PYTHONUTF8=1`을 등록한다.
- 실제 에이전트(`claude -p`)는 6-9의 루프 한 번만 학생이 자기 계정으로 돌린다(시도 상한 3, 루프 전체 0.60달러). 2-8의 `stream-json`, 7-3의 실제 요약, 8절의 cron은 교수 시연이며 그 기록을 `실습재료/시연기록/`으로 배포한다.
- Claude Code는 공식 설치 프로그램으로 설치한 `claude`(Windows에서는 `claude.exe`)를 전제한다(부록 A-3). 루프는 셸을 거치지 않고 명령을 실행하므로, npm으로 설치해 `claude.cmd`만 있는 경우 「에이전트 명령을 찾지 못하였다」로 멈춘다.

## 확인한 환경

2026-11-17, Windows 11, Git Bash, Python 3.13.7, pytest 9.2.0, git 2.55.0.windows.5, Claude Code 2.1.296. 가짜 에이전트로 네 경로와 루프 테스트를 실행하였다. 실제 `claude -p`의 실행은 확인하지 못하였다(교수용 강의안 「확인하지 못한 것」).
