# Agent_05장: 외부 도구의 연결 (MCP)

「AI에이전트 기획 및 개발」 5장의 실습 키트다. `jobprep`의 운영 기록(`logs/`)을 읽기 전용으로 내놓는 MCP 서버 `mcp/ops_server.py`를 완성하고, 단독 테스트로 판정한 뒤, 저장소의 `.mcp.json`으로 Claude Code에 연결한다. 강의안은 `Agent_05장_학생용.md`이다.

## 받기

키트 저장소(부록 A-7)에서 받는다. `cp -rn`은 이미 있는 파일을 덮어쓰지 않는다.

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_05장 ~/kits/
```

## 구성

```text
Agent_05장/
├── README.md                    이 파일
├── requirements-mcp.txt         mcp==2.3.0 (저장소의 requirements.txt에 덧붙인다)
├── mcp/ops_server.py            서버 골격. error_summary만 완성, 나머지 셋은 9-2절에서 완성
├── tests/test_ops_server.py     고정 테스트 10개(고치지 않는다)
├── 설정/
│   ├── mcp.json                 프로젝트 범위 .mcp.json 견본(command는 python, 서버 경로는 ${CLAUDE_PROJECT_DIR:-.}. 9-5절)
│   ├── settings_MCP규칙.json     MCP 도구의 권한 규칙(allow 3, ask 1, deny 1)
│   └── merge_settings.py        위 규칙을 .claude/settings.json에 더하는 스크립트
├── 도구/show_tools.py            stdio 서버의 도구·리소스·프롬프트 목록과 설명을 보이고, --call로 도구 하나를 부른다
├── 시연/
│   ├── stdio_요청.jsonl          stdio로 직접 보내 볼 MCP 요청 4줄(3-2절)
│   └── weather_server.py        도구 설명에 지시를 숨긴 위험 견본(연결하지 않는다. 10-3절, 교수 화면)
├── MCP점검_양식.md               산출물 docs/운영/MCP점검.md의 양식
├── 프롬프트_견본.md               Claude Code에 보내는 프롬프트 P1~P5
├── 기준산출물_안내.md
├── 기준산출물/                    3·4장 결과(3장 교수 완성본의 CLAUDE.md·rules·settings.json, 4장 플러그인 jobprep-ops·마켓플레이스)
└── 교수/                         교수 전용(키트 저장소에 올리지 않는다)
```

## 순서

명령은 내 PC의 터미널(Windows는 Git Bash, macOS는 기본 셸)에서 저장소의 가상 환경을 켠 뒤(`source .venv/Scripts/activate`, macOS는 `source .venv/bin/activate`) `python`으로 부른다. `python3`과 `.venv/bin/python …` 같은 경로 호출은 쓰지 않는다.

1. 0절: 키트 받기, 앞 장 산출물 확인(없으면 `기준산출물/`), `requirements-mcp.txt`를 덧붙여 설치.
2. 6-4절(따라 하기 1): 골격·테스트·양식을 복사하고 고정 테스트의 일부(`-k "stdio or 폴더_밖 or 형식이"`)를 돌린다.
3. 7-7절(따라 하기 2): `claude mcp add --scope project`로 등록하고 `claude mcp get`으로 승인 대기를 본다.
4. 9절(핵심 실습): Red 확인 → Claude Code로 구현(P1) → 설명 개선 → 단독 테스트 통과·커밋 → 승인과 연결, Windows에서 실패하는 명령 경로를 `설정/mcp.json`의 꼴로 고침 → 장애 조사(P2) → 기록과 대조 → 권한 규칙(`설정/merge_settings.py`) → 거부 시험(P3, P4) → 점검 기록·커밋.
5. 3-2절의 `시연/stdio_요청.jsonl`, 4절의 연습 서버, 10-3절의 `시연/weather_server.py`는 교수 화면으로 읽는다(직접 해 보는 것은 선택).

## 기대하는 테스트 화면

골격 상태(9-1절)에서는 실패가 정상이다.

```text
$ python -m pytest tests/test_ops_server.py
FAILED tests/test_ops_server.py::test_도구_설명은_두_문장_이상이고_모든_인자에_설명이_있다
FAILED tests/test_ops_server.py::test_status_counts는_상태_코드별로_센다 - ...
FAILED tests/test_ops_server.py::test_slow_requests는_기준_이상만_고른다 - ...
FAILED tests/test_ops_server.py::test_read_log는_시각_앞뒤의_줄만_보여_준다
FAILED tests/test_ops_server.py::test_결과는_줄_수_상한을_넘지_않는다 - ...
5 failed, 5 passed
```

9-2절 뒤에는 `1 failed, 9 passed`(설명 테스트만 실패), 9-3절 뒤에는 `10 passed`, 저장소 전체는 `53 passed`(기준 저장소 43 + 10)가 나온다.

## 주의

- 저장소의 `mcp/` 폴더에 `__init__.py`를 만들지 않는다. SDK 패키지 이름 `mcp`와 겹쳐 `import mcp`가 깨진다.
- 서버 코드에서 `print()`를 쓰지 않는다. stdio 서버의 표준 출력은 MCP 메시지 전용이다.
- `시연/weather_server.py`는 Claude Code에 연결하지 않는다.
- 공식 SDK 2.x는 `from mcp.server import MCPServer`를 쓴다. 1.x의 `FastMCP`와 제3자 패키지 `fastmcp`는 쓰지 않는다.
- `.mcp.json`의 `command`에 `.venv/bin/python`(macOS·리눅스)이나 `.venv/Scripts/python.exe`(Windows)를 적으면 다른 OS의 팀원에게서 연결이 실패한다. 견본처럼 `"command": "python"`으로 두고, Claude Code는 가상 환경을 켠 터미널에서 연다.
- 키트 저장소에는 `교수/`가 없다. `tests/test_ops_server.py`는 `교수/`를 읽지 않으므로 학생 키트에서 그대로 돈다.
