# Agent_09장 키트: 에이전트 루프의 구조 (API와 도구 호출)

「AI에이전트 기획 및 개발」 9장의 실습 재료이다. 핵심 실습은 도구 두 개(`search_jobs`, `read_doc`)를 쓰는 최소 에이전트 루프 `agent_loop/`를 학습자의 저장소 `~/agent-lab/jobprep/`에 만들고, 모의 모델로 테스트를 통과시키며, 골격의 경로 탈출(`read_doc`이 `../../README.md`를 읽는 것)을 재현해 막는 것이다. 받는 법과 순서는 강의안 0절과 부록 A-7을 따른다(`git -C ~/kits-repo pull` 뒤 `cp -rn ~/kits-repo/Agent_09장 ~/kits/`).

## 들어 있는 것

| 경로 | 쓰는 절 | 내용 |
|---|---|---|
| `시작/agent_loop/` | 0절, 7절 | 골격. `loop.py`(TODO 1·2), `tools.py`(TODO 3·4), `fake_model.py`(완성), `__init__.py`. 저장소에 `agent_loop/`로 복사한다 |
| `시작/tests/test_agent_loop.py` | 6절, 7절 | 루프 테스트 39개. 저장소 `tests/`에 복사한다 |
| `참고/견본기록_normal.json` | 3절 | 완성된 루프가 `normal` 시나리오로 남긴 대화 기록. TODO를 끝내기 전에 왕복 메시지의 모양을 읽는 데 쓴다 |
| `참고/react_text_loop.py` | 9절(읽기) | 글 서식으로 도는 ReAct 루프(2026년 2학기판 LLM 8주차 재료의 완성본). `mock`으로 실행 |
| `참고/sdk_agent.py`, `참고/test_sdk_tools.py`, `참고/requirements-sdk.txt` | 10절(읽기, 설치는 선택) | 같은 에이전트의 Claude Agent SDK 판, 모델 없이 도는 처리 함수 테스트, SDK 판 고정(0.2.182) |
| `참고/subagent_sketch.py` | 11절(읽기) | 도구 하나 안에서 새 루프를 돌려 요약만 돌려주는 서브에이전트의 원리(모의 모드) |
| `도구/loop_map.py` | 11절(읽기) | `.claude/settings.json`의 권한 규칙과 훅이 루프의 어느 단계에 끼는지 출력한다. 읽기만 한다 |
| `기준산출물/.claude/` | 11절 | 7장에서 조립한 하네스의 `settings.json`(훅 `protect.sh`, `run_tests.sh`, `stop_gate.sh`)과 `agents/reviewer.md`(검토 규칙 RV1~RV8). 7장 키트 `조립/`의 사본이다. `loop_map.py`에 넘겨 읽는 용도이며 저장소에 복사하지 않는다 |
| `시연기록/` | 7-9, 10-4 | 교수 시연(실제 모델)의 기록을 교수가 키트 저장소에 올리는 곳. 처음에는 `README.md`만 있다 |
| `루프대조_양식.md` | 7~11절 | `agent_loop/루프대조.md`의 양식 |
| `교수/` | 교수 | TODO 정답, 시연 순서, 대조표 예시, 흉내 서버. 학생용 키트 저장소에 넣지 않는다 |

## 단계와 기대하는 테스트 결과

골격은 일부러 실패하는 상태로 배포한다(집필 기준 8절의 예외). 저장소 폴더에서 가상 환경을 켜고 `python -m pytest -q tests/test_agent_loop.py`를 돌린 끝줄은 단계마다 다음과 같다. Windows에서는 심볼릭 링크를 만들 수 없는 계정이면 링크 탈출 테스트 하나가 건너뛰어져 `1 skipped`가 붙는다.

| 단계(강의안 절) | 고치는 곳 | 끝줄(Windows) | 끝줄(macOS) |
|---|---|---|---|
| 복사 직후(0-2) | 없음 | `25 failed, 13 passed, 1 skipped` | `26 failed, 13 passed` |
| TODO 1(7-2) | `loop.py`: tool_result를 모아 user 메시지로 돌려준다 | `22 failed, 16 passed, 1 skipped` | `23 failed, 16 passed` |
| TODO 2(7-3) | `loop.py`: end_turn과 그 밖의 stop_reason으로 끝낸다 | `11 failed, 27 passed, 1 skipped` | `12 failed, 27 passed` |
| TODO 3(7-4) | `tools.py`: `search_jobs`의 설명 | `9 failed, 29 passed, 1 skipped` | `10 failed, 29 passed` |
| TODO 4(7-6) | `tools.py`: `read_doc`의 경로 검사 두 겹 | `38 passed, 1 skipped` | `39 passed` |

TODO 3까지 마친 뒤 남는 실패 아홉 개는 모두 `test_read_doc_rejects_paths_outside_docs`(경로 아홉 개)이다. 이것이 7-5절에서 재현하는 문제이다.

## 실행 (저장소 폴더, 가상 환경을 켠 터미널)

```bash
LLM_FAKE=1 python -m agent_loop.loop "질문" --scenario normal      # 시나리오: normal parallel bad_doc bad_args escape runaway truncated note
LLM_FAKE=1 python -m agent_loop.loop "질문" --scenario runaway --max-turns 3
LLM_FAKE=1 python -m agent_loop.loop "메모해 줘" --scenario note --with-note   # 승인 요청이 뜬다
python ~/kits/Agent_09장/참고/react_text_loop.py mock
python ~/kits/Agent_09장/도구/loop_map.py ~/kits/Agent_09장/기준산출물/.claude/settings.json ~/kits/Agent_09장/기준산출물/.claude/agents
```

키트의 파이썬 스크립트는 표준 출력을 UTF-8로 내므로 Windows에서 파이프로 넘겨도 한글이 깨지지 않는다. `pytest` 등 다른 파이썬 프로그램의 출력은 부록 A-4-4의 `PYTHONUTF8=1`이 필요하다. `--save`의 기록 파일은 Windows에서도 줄 끝이 LF이다.

## 실제 모델과 실행 상한

모의 모델이 기본이며, 핵심 실습과 모든 확인은 키 없이 끝난다. 실제 API는 Console의 키를 각자 발급한 학습자만 7-9절의 명령 하나(`LLM_FAKE=0 python -m agent_loop.loop "…" --save agent_loop/runs/real.json`)를 1회 실행한다(편성표 §3, 부록 A-12-3). 키는 저장소의 `.env`에만 둔다(부록 A-11). Agent SDK 판(`sdk_agent.py`)의 실제 실행은 교수 시연이며, 교수는 두 실행의 기록을 키트 저장소의 `Agent_09장/시연기록/`에 올린다. 키가 없는 학습자는 `git -C ~/kits-repo pull` 뒤 그 기록을 들여온다.

## 확인한 환경

2026-11-17, Windows 11, Git Bash, Python 3.13.7, 기준 저장소의 `requirements.txt`(anthropic 2.8.0, pytest 9.2.0 등)에서 위 표의 Windows 열을 확인하였다. macOS 열은 2026-11-14에 WSL Ubuntu(Python 3.12.3)에서 확인한 리눅스 값이다(링크 테스트가 실행되는 환경). 10절의 SDK는 스크래치 가상 환경에 claude-agent-sdk 0.2.182를 설치해 `tests/test_sdk_tools.py`가 `3 passed`인 것을 확인하였다. 실제 모델 호출은 하지 않았다.
