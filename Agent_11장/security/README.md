# security/: 11장 보안 실습 자료

이 폴더는 「AI에이전트 기획 및 개발」 11장의 간접 프롬프트 주입 재현 자료와 검사 도구이다.
실습은 저장소 안에서만, 실습용 가짜 키로만 한다. 실제 API 키를 쓰지 않고 네트워크에 접속하지 않는다.

| 경로 | 내용 |
|---|---|
| `lab/naive_agent.py` | 입력 문서 속 지시를 그대로 따르는 가짜 에이전트. 모델을 부르지 않는다 |
| `lab/run_matrix.py` | 시나리오 넷을 방어층마다 돌려 결과 표를 낸다(임시 폴더에서 돈다) |
| `lab/scenarios/` | 지시를 숨긴 입력 넷: 이슈 본문 둘, 공고 JSON 하나, 취업 자료 문서 하나 |
| `lab/make_fake_secret.py` | `secrets/실습용_가짜키.txt`(LABKEY- 값)를 만든다 |
| `lab/perm_sim.py`, `lab/globmatch.py` | 3장의 권한 규칙 판정 모의기 사본(가짜 에이전트의 rules 층) |
| `lab/try_hook.py`, `lab/hook_samples/`, `lab/gap_samples/` | PreToolUse 훅을 견본 입력으로 단독 시험한다. gap_ 견본은 알려진 틈이다 |
| `scan_secrets.py` | 비밀 탐지의 입구(13장 CI가 부른다). 본체는 `tools/scan_secrets.py` |
| `tools/scan_secrets.py` | 커밋될 수 있는 파일(과 기록)에서 키 모양을 찾는다. 예외는 `allowlist.txt` |
| `tools/check_output.py` | 내보낼 글에서 비밀, 유출 링크, 실행될 HTML, 보이지 않는 문자를 찾는다 |
| `tools/check_threat_model.py` | `docs/운영/위협모델.md`의 형식을 검사한다 |
| `tools/secret_patterns.py` | 검사 도구들이 함께 쓰는 키 모양 목록 |
| `logs/` | 가짜 에이전트의 감사 기록(JSONL). 가짜 키는 가려서 남긴다 |
| `결과기록.md` | 재현 결과(양식: `결과기록_양식.md`) |

`secrets/`와 `security/out/`(가짜 에이전트가 쓴 답글과 바깥 주소 기록)은 `.gitignore`로 저장소에 올리지 않는다.

비밀 정보 보호 훅 자체(`block_secrets.py`, 실행기 `block_secrets.sh`)는 이 폴더가 아니라 저장소의 `.claude/hooks/`에 둔다(강의안 11-5절). `lab/try_hook.py`는 그 훅을 견본 20개로 시험한다.
