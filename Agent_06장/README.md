# 6장 키트: 훅과 서브에이전트

「AI에이전트 기획 및 개발」 6장(학사 7주차)의 실습 키트이다. 강의안은 `Agent_06장_학생용.md`이다. 키트는 키트 저장소에서 저장소 밖의 `~/kits/Agent_06장/`로 받고(부록 A-7), 필요한 파일만 저장소(`~/agent-lab/jobprep/`)로 옮긴다.

```bash
git -C ~/kits-repo pull
cp -rn ~/kits-repo/Agent_06장 ~/kits/
```

## 들어 있는 것

| 경로 | 내용 | 저장소로 옮길 곳 |
|---|---|---|
| `hooks/protect.sh` | PreToolUse 훅. 보호 경로(`.env`, 동결 기록, 동결된 테스트, `.git/`)의 편집을 종료 코드 2로 막는다. 경로는 슬래시 꼴로 맞추고 대소문자 구별 없이 비교한다 | `.claude/hooks/` |
| `hooks/protected.txt` | protect.sh가 읽는 보호 경로 패턴 목록 | `.claude/hooks/` |
| `hooks/run_tests.sh` | PostToolUse 훅. 파이썬 파일을 고친 뒤 문법 검사, 동결 검사, 관련 테스트를 돌린다 | `.claude/hooks/` |
| `hooks/stop_gate.sh` | Stop 훅([선택]). 테스트가 실패한 채로 끝내려 하면 한 번 더 일하게 한다(`stop_hook_active`로 반복을 끊는다) | `.claude/hooks/` |
| `hooks/check_hooks.sh` | 세 훅을 견본 입력으로 실행해 종료 코드와 출력을 확인하는 점검 스크립트(18개 사례) | `.claude/hooks/` |
| `hooks/samples/*.json` | 훅 입력 JSON 견본(Claude Code 문서의 입력 형식을 본뜸). `__PROJECT__`는 점검 스크립트가 저장소 경로(`C:/…` 꼴)로, `__PROJECT_WIN__`은 Windows 꼴(`C:\…`)로 바꾼다 | `.claude/hooks/samples/` |
| `훅설정.json` | settings.json에 더할 hooks 조각(PreToolUse, PostToolUse) | `도구/merge_hooks.py`로 합친다 |
| `훅설정_stop.json` | 개인 설정(settings.local.json)에 더할 Stop 훅 조각 | [선택] |
| `도구/merge_hooks.py` | 설정 파일에 훅 조각을 합친다. 다른 키는 그대로 둔다 | 키트에서 실행 |
| `도구/check_agent.py` | 서브에이전트 정의 파일의 프런트매터 검사(`--read-only`로 읽기 도구만인지 확인) | 키트에서 실행 |
| `reviewer_양식.md` | 검토 전담 서브에이전트의 양식. 「 」를 채운다 | `.claude/agents/reviewer.md` |
| `검토자검증_양식.md` | 검토자 검증 기록 양식 | `docs/운영/검토자검증.md` |
| `검토연습/검토연습.patch` | 위반 다섯 곳을 심은 변경 묶음. `review-drill` 브랜치에만 적용한다 | 적용만 한다 |
| `시연기록/` | 교수 시연의 검토 기록(수업 중에 두 번 나누어 올라온다) | 읽기만 한다 |
| `기준산출물/` | 2~5장을 마치지 못한 학생용 견본(동결 기록과 검사기, CLAUDE.md, settings.json, 5장의 MCP 서버 완성본과 `.mcp.json`) | `기준산출물/README.md`를 본다 |

교수용 사본에는 `교수/`(정답, 완성한 reviewer.md와 1회차 시연용 정의, 시연 기록을 만드는 스크립트와 견본 기록, 패치를 만든 스크립트)가 더 있다. 키트 저장소에는 올리지 않는다.

## 순서

1. 0절: 키트를 받고 저장소 상태와 앞 장 산출물을 확인한다. 없으면 `기준산출물/`을 복사한다.
2. 4-3절(따라 하기 1): 훅 세 개를 `.claude/hooks/`에 넣고 견본 입력으로 하나씩 실행한다. `protected.txt`에 `data/jobs.json`을 더한다.
3. 7절(따라 하기 2): `bash .claude/hooks/check_hooks.sh`로 18개 사례를 점검하고, `도구/merge_hooks.py`로 settings.json에 등록하고, 디버그 기록으로 훅이 도는 것을 본다.
4. 10절(핵심 실습): Claude Code에서 훅을 관찰하고, `reviewer_양식.md`로 검토자를 만들고, `review-drill` 브랜치에 검토연습 패치를 적용해 검토 대상(diff)을 만들고, `시연기록/`의 기록으로 판정한 뒤 놓친 위반의 까닭을 자기 정의 파일에서 고치고 한 번 투입해 확인한다.

## 교수 시연과 시연 기록

같은 정의를 같은 대상에 여러 번 돌리는 검토자 실행(정상 변경, 1회차 세 번, 2회차, 규칙 밖의 위반)은 교수 시연이다(편성표 결정 11의 실행 상한). 교수는 기록을 두 번에 나누어 키트 저장소의 `Agent_06장/시연기록/`에 올린다. 학생은 올라올 때마다 위의 두 줄(`git pull`과 `cp -rn`)을 다시 실행한다. `cp -n`이므로 이미 받은 파일은 덮어쓰지 않고 새 기록만 들어온다.

학생이 직접 하는 것: 정의 파일 쓰기와 불러오기, 훅 관찰, 고친 자기 정의로 검토자를 한 번 투입하기(Claude Code 대화형 세션).

## 실행 환경

- 훅은 bash 스크립트이다. Windows의 Claude Code는 셸 형식의 훅 명령을 Git Bash로 실행한다(Git for Windows가 없으면 PowerShell로 돌아 이 훅은 실행되지 않는다). macOS와 리눅스는 `sh -c`로 실행한다.
- 입력 JSON은 파이썬으로 읽는다. 훅은 가상 환경을 켜지 않은 셸에서 돌므로 저장소의 `.venv/Scripts/python.exe`(Windows)를 먼저, 없으면 `.venv/bin/python`(macOS·리눅스)을 쓴다(부록 A-9-2). Windows에서 `python3`은 Microsoft Store의 실행 별칭이거나 다른 판의 파이썬일 수 있어 마지막에만 찾는다.
- Windows의 Git은 `chmod +x`를 기록하지 않는다(`core.filemode=false`). 팀원이 macOS·리눅스에서 받아도 훅이 실행되게 커밋할 때 `git add --chmod=+x .claude/hooks/*.sh`를 쓴다.
- 키트의 `protected.txt`에는 `data/jobs.json`이 없다. 강의안 4-3절에서 학생이 직접 더한다. 더하기 전에 점검 스크립트를 돌리면 「보호: 공고 데이터」 한 사례가 FAIL이고(의도한 실패), 더한 뒤에는 18개가 모두 PASS이다(동결 검사기 `tools/test_guard.py`가 없으면 17개).
- 2026-11-17, Windows 11의 Git Bash(GNU bash 5.3.15, Python 3.13.7)에서 모든 점검을 실행하였다. 집필 PC에서 `check_hooks.sh` 전체가 약 1분 30초, protect.sh 한 번이 1~3초, run_tests.sh 한 번이 10~15초 걸렸다. macOS에서의 실행은 수업 전에 교수가 확인한다.
