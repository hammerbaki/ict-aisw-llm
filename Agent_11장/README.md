# Agent_11장 키트: 에이전트의 보안

「AI에이전트 기획 및 개발」 11장(학사 13주차)의 실습 키트이다. 간접 프롬프트 주입을 실습용 가짜 비밀과 가짜 에이전트로 재현하고, 거부 규칙·PreToolUse 훅·도구 제한·출력 검사로 막은 뒤, 위협 모델을 쓴다. 실제 API 키를 쓰지 않고, 네트워크에 접속하지 않으며, 실제 모델을 부르지 않는다. 모든 실습은 내 PC(Windows의 Git Bash 또는 macOS 터미널)에서 한다.

## 받는 법

키트 저장소를 1주차에 `~/kits-repo`로 클론해 두었다고 전제한다(부록 A-7).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_11장 ~/kits/
```

## 구성과 쓰는 순서

| 경로 | 강의안 절 | 저장소로 옮기는 곳 | 내용 |
|---|---|---|---|
| `기준산출물/`, `기준산출물_안내.md` | 0 | 저장소 맨 위(`cp -rn 기준산출물/. .`) | 3~7장을 마치지 못한 학습자용 설정, 훅, 서브에이전트, MCP 서버(7장 키트의 기준산출물과 조립본) |
| `security/` | 4, 11-2 | `security/` | 가짜 에이전트(`lab/naive_agent.py`), 시나리오 넷, 가짜 키 생성기, 판정 모의기 사본, 훅 단독 시험기와 견본, 비밀 탐지·출력 검사·위협 모델 검사 도구, 결과 기록 양식 |
| `tests/` | 11-3 | `tests/` | `test_security_lab.py`, `test_security_tools.py`. 대책을 적용하기 전에는 18개가 실패한다(기대하는 실패) |
| `settings_보안추가.json`, `도구/merge_security.py` | 6-2, 11-4 | `.claude/settings.json`에 합친다 | 거부 규칙 12개와 PreToolUse 훅 등록 두 묶음(`onFailure: block`) |
| `hooks/block_secrets.py`, `hooks/block_secrets.sh` | 6-3, 11-5 | `.claude/hooks/` | 비밀 정보 보호 훅과 그 실행기(파이썬을 고르고, 판단할 수 없으면 막는다) |
| `agents/issue-triage.md` | 6-4, 11-6 | `.claude/agents/` | 읽기 도구만 가진 분류 서브에이전트 |
| `github/dependabot.yml` | 9-4, 11-10 | `.github/` | Dependabot 버전 업데이트 설정 |
| `위협모델_양식.md` | 10, 11-11 | `docs/운영/위협모델.md` | 위협 모델 양식(아홉 절) |
| `시연기록/` | 7-4, 11 | (옮기지 않는다) | 교수 시연(실제 모델의 반응, 샌드박스)의 대화 기록이 올라오는 곳 |

## 대책 적용 전의 테스트 (기대하는 실패)

`tests/`를 저장소에 복사한 직후 `python -m pytest -q`는 `18 failed, 68 passed`(기준 저장소 43개 기준)로 끝난다. 실패의 까닭은 「대책 파일이 없다」, 「deny에 Read(./secrets/**)이 없다」, 또는 유출 판정이다. 11-4~11-6절(거부 규칙 → 15 failed, 훅 → 8 failed, 분류 서브에이전트 → 0)을 마치면 모두 통과한다.

## Windows에서 다르게 하는 것

- 가상 환경을 켠 터미널에서 `python`으로 부른다(`source .venv/Scripts/activate`, macOS는 `.venv/bin/activate`). `python3`은 Git Bash에 없다.
- 파이썬 출력을 `|`로 넘기는 명령이 많으므로 부록 A-4-4의 `PYTHONUTF8=1`이 켜져 있어야 한다.
- 비밀 정보 보호 훅은 `bash .../block_secrets.sh`로 등록한다. 실행기가 `.venv/Scripts/python.exe` → `.venv/bin/python` → `python` → `python3` 순으로 파이썬을 고른다. 훅은 Windows 꼴 경로(`C:\…`, `/c/…`), 대소문자(`.ENV`), `curl.exe`, PowerShell 명령을 다룬다(견본 `block_read_env_windows`, `block_powershell_env`).
- 샌드박스는 Windows에서 돌지 않으므로 설명과 교수 시연으로 본다(부록 A-1-2). `make_fake_secret.py`의 파일 권한 설정(`600`)은 Windows에서 효과가 없다.

## 안전 수칙

- 비밀은 `make_fake_secret.py`가 만드는 `LABKEY-` 값뿐이다. 실제 키를 `secrets/`에 넣지 않는다.
- `secrets/`와 `security/out/`은 `.gitignore`에 넣는다(강의안 4-1절). 공용 PC에서는 수업이 끝나면 `secrets/`와 `security/out/`을 지운다.
- 시나리오의 바깥 주소는 문서용 예약 도메인 `collector.example`이며, 가짜 에이전트는 요청하지 않고 기록만 남긴다.
- 키트의 테스트는 실제 서비스의 키 형식을 실행 중에 이어 붙여 만든다. 파일에 키 모양을 그대로 적지 않는다.

## 확인한 환경

2026-11-17, Windows 11의 Git Bash 5.3, Python 3.13.7, git 2.55, Claude Code 2.1.296에서 1장 기준 저장소 `jobprep`에 기준산출물을 더해 강의안 0~11절의 명령을 실행하였다(키트 저장소는 `교수/`를 뺀 로컬 사본으로 흉내). 실제 모델은 부르지 않았다. macOS에서는 실행하지 않았다.
