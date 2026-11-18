# Agent_01장 키트: 운영 요건과 역할 정의

「AI에이전트 기획 및 개발」 1장(학사 2주차)의 실습 키트이다. 학기 내내 운영할 기준 저장소 `jobprep`과, 1장의 핵심 실습에서 쓰는 양식과 형식 검사 도구가 들어 있다. 실습은 내 PC에서 한다(Windows는 VS Code의 Git Bash, macOS는 기본 셸. 부록 A-3, A-4).

## 들어 있는 것

| 경로 | 내용 | 쓰는 곳 |
|---|---|---|
| `jobprep/` | 기준 저장소. 「LLM 서비스 개발」의 여러 단원에서 다룬 기능(공고 모아보기, API 서버, 문서 요약, 질의응답)을 「취업 준비 지원 서비스」 하나로 묶어 정리한 것(웹, FastAPI API, 질의응답 검색, 요구사항명세서, 운영 기록 견본, 테스트 43개) | 2절에서 `~/agent-lab/jobprep/`으로 복사해 자기 저장소로 만든다 |
| `ops/check/check_ops.py` | 운영 요건 명세와 역할 정의서의 형식 검사 도구 | 8-5절(읽기), 11절. 저장소의 `ops/check/`로 복사한다 |
| `ops/check/test_check_ops.py` | 형식 검사 도구의 테스트 16개 | 11절에서 `python -m pytest -q ops/check`로 실행한다 |
| `운영요건_양식.md` | 운영 요건 명세의 양식 | 11절. `docs/운영/운영요건.md`로 복사해 채운다 |
| `역할정의_양식.md` | 역할 정의서의 양식 | 11절. `docs/운영/역할정의.md`로 복사해 채운다 |
| `기준저장소_안내.md` | 기준 저장소의 구조 요약(집필자와 교수용 참고) | 필요할 때 읽는다 |

## 쓰는 순서

명령은 모두 `[터미널]`(Windows의 Git Bash 또는 macOS의 터미널)에서 실행한다. macOS에서는 가상 환경을 만들 때 `python3 -m venv .venv`, 켤 때 `source .venv/bin/activate`로 바꾼다.

1. 키트를 받는다(강의안 0절, 부록 A-7). 키트 저장소는 1주차에 `~/kits-repo`로 클론해 두었다고 전제한다.

   ```bash
   git -C ~/kits-repo pull
   mkdir -p ~/kits ~/agent-lab
   cp -rn ~/kits-repo/Agent_01장 ~/kits/
   ```

2. 기준 저장소를 작업 공간으로 복사하고 Git 저장소로 만든다(강의안 2-1절, 부록 A-8).

   ```bash
   cp -rn ~/kits/Agent_01장/jobprep ~/agent-lab/
   cd ~/agent-lab/jobprep
   git init
   git add .
   git commit -m "chore: 기준 저장소 jobprep을 받음"
   ```

3. 가상 환경을 만들고 테스트를 돌린다(강의안 2-2절, 부록 A-9). 결과의 마지막 줄이 `43 passed`이면 된다.

   ```bash
   python -m venv .venv
   source .venv/Scripts/activate
   python -m pip install -r requirements.txt
   cp -n .env.example .env
   LLM_FAKE=1 python -m pytest -q
   ```

4. 형식 검사 도구와 양식을 저장소로 옮긴다(강의안 11절).

   ```bash
   cp -rn ~/kits/Agent_01장/ops ~/agent-lab/jobprep/
   cp -n ~/kits/Agent_01장/운영요건_양식.md ~/agent-lab/jobprep/docs/운영/운영요건.md
   cp -n ~/kits/Agent_01장/역할정의_양식.md ~/agent-lab/jobprep/docs/운영/역할정의.md
   python -m pytest -q ops/check
   ```

   `python -m pytest -q ops/check`는 `16 passed`이다. 저장소의 `python -m pytest -q`(인자 없이)는 `pytest.ini`의 `testpaths = tests`에 따라 `tests/`만 모으므로 그대로 `43 passed`이다.

5. 양식을 채우며 형식 검사를 되풀이한다.

   ```bash
   python ops/check/check_ops.py reqs docs/운영/운영요건.md
   python ops/check/check_ops.py roles docs/운영/역할정의.md --reqs docs/운영/운영요건.md
   ```

## 형식 검사 도구가 보는 것

| 대상 | 검사 |
|---|---|
| 운영 요건(`reqs`) | ID 형식 `OR-<SEC\|REL\|CON\|REP>-<두 자리>`와 중복, 분류 칸(보안·신뢰성·일관성·재현성)과 ID의 일치, EARS 문형 이름과 문장의 표지(동안, ~면, 경우, 만약), 「~야 한다」로 끝나는지, 측정 방법 칸이 비었는지, 전체 15개 이상·분류마다 3개 이상. 모호한 말(적절히, 빠르게 등)은 경고 |
| 역할 정의(`roles`) | `### R<번호> 이름` 제목의 역할 수(5개 이상), 역할마다 권한·입력·출력·완료 조건·사람 승인 지점 칸, 관련 운영 요건 ID가 운영 요건 명세에 있는지. 권한 칸에 「금지」가 없으면 경고 |

이 도구는 형식만 본다. 요구가 옳은지, 측정 방법이 실제로 잴 수 있는지는 사람이 판정한다.

## 기대하는 실패 화면

양식을 복사한 직후에 검사하면 자리 표시(「 」)가 남아 있어 실패한다. 정상이다.

```text
운영요건.md: 요건 16개 (보안 4 · 신뢰성 4 · 일관성 4 · 재현성 4)
  오류 44행 OR-SEC-01: 요구 문장이 비어 있다
  오류 44행 OR-SEC-01: 측정 방법이 비어 있다
  ...
  결과: 오류 32개
```

다 채우면 마지막 줄이 `결과: 통과`가 된다(경고는 남아도 통과이다).

## 교수 전용

`교수/` 폴더(예시 답안)는 학생 배포본에 넣지 않는다. 공개 사이트의 키트 목록(`KITS`)에도 넣지 않는다.
