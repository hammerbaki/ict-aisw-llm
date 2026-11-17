# 7장 키트: 하네스의 설계와 구축 (Agent_07장)

「AI에이전트 기획 및 개발」 7장(학사 9주차)의 실습 자료이다. 1~6장에서 만든 부품을 `jobprep` 저장소 하나에 하네스로 조립하고, 같은 작업을 하네스가 없을 때와 있을 때로 실행해 비교한다. 강의안은 `Agent_07장_학생용.md`이다. 키트는 저장소 밖의 `~/kits/Agent_07장/`에 받고, 필요한 파일만 저장소(`~/agent-lab/jobprep/`)로 옮긴다.

## 받기

내 PC의 Git Bash(macOS는 터미널)에서 키트 저장소를 최신으로 받고 이 장의 폴더를 `~/kits/`로 복사한다(부록 A-7-3).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_07장 ~/kits/
```

교수 시연의 실행 기록(`시연기록/`)은 수업 중에 키트 저장소로 올라온다. 그때 같은 방법으로 한 번 더 받는다(강의안 7-8절).

```bash
git -C ~/kits-repo pull
cp -rn ~/kits-repo/Agent_07장/시연기록 ~/kits/Agent_07장/
```

## 들어 있는 것

```text
Agent_07장/
├── README.md                  이 문서
├── 하네스설계서_양식.md        → docs/운영/하네스설계서.md 로 복사해 채운다
├── 하네스비교_양식.md          → docs/운영/하네스비교.md 로 복사해 채운다
├── 기준산출물/                2~6장 산출물의 견본(앞 장 산출물이 없는 학습자용). 출처는 기준산출물/README.md
├── 조립/                      7장에서 고친 부품: .claude/settings.json(Stop 훅을 공유 설정으로),
│                              .claude/agents/reviewer.md(규칙 RV7·RV8 추가), CLAUDE.md(지시와 강제의 중복 정리)
├── ops/harness/               측정 도구 → 저장소의 ops/harness/ 로 복사한다
│   ├── harness_check.sh       조립 점검(모델을 부르지 않는다. 6장 check_hooks.sh를 함께 돌린다)
│   ├── prepare_runs.sh        실험 저장소 만들기(작업 × on/off × 반복. TASKS=T2로 작업을 고른다)
│   ├── run_task.sh            실험 한 건을 헤드리스로 실행(claude -p, stream-json 기록). 실제 모델을 부른다
│   ├── judge.py               판정: 인수 검사, 전체 테스트, 규칙 검사
│   ├── check_rules.py         규칙 위반 검사(V1~V8)
│   ├── collect.py             기록 집계 → 마크다운 표
│   ├── 수동기록_양식.csv       대화형 실행과 사람 개입의 기록
│   ├── 작업카드/T1.md T2.md T3.md
│   ├── 인수검사/              작업별 판정 기준(실험 저장소에서는 지운다)
│   ├── 견본기록/              예시 데이터(실제 실행 기록이 아니다). 집계 연습용
│   └── tests/                 측정 도구의 테스트(9개)
├── 충돌연습/                  일부러 충돌을 넣은 규칙·설정·스킬(읽기만 한다)
├── 플러그인/                  하네스를 묶은 플러그인 jobprep-harness와 마켓플레이스 견본(8절, 읽기와 [선택])
└── 시연기록/                  (수업 중에 올라온다) 교수 시연의 실행 기록, 판정, diff, README
```

## 쓰는 순서

명령은 모두 저장소 맨 위(`~/agent-lab/jobprep`)에서, 가상 환경을 켠 터미널(Windows `source .venv/Scripts/activate`, macOS `source .venv/bin/activate`)에서 친다.

1. 0절: 키트를 받고, 앞 장 산출물이 없으면 `기준산출물/`을 저장소에 복사한다. `ops/harness/`와 양식 둘을 저장소로 옮기고 `python -m pytest ops/harness/tests`가 `9 passed`인지 본다.
2. 3-7절(따라 하기 1): 하네스 설계서의 4·5·6·9절(판정 기준 포함)을 쓰고 커밋한다.
3. 6-7절(따라 하기 2): `ops/harness/견본기록/`으로 `collect.py`를 돌리고 기록 한 건의 도구 호출을 뽑는다.
4. 7절(핵심 실습): 작업 브랜치 → `bash ops/harness/harness_check.sh`(처음에는 「Stop 훅」 한 항목이 실패한다) → `조립/` 반영 → 점검 `실패 0` → 설계서 8절과 태그 `harness-v1` → `TASKS=T2 bash ops/harness/prepare_runs.sh harness-v1` → `bash ops/harness/run_task.sh T2-off-1`, `T2-on-1`(실행 상한: 이 두 번) → `python ops/harness/judge.py`로 판정 → `시연기록/`의 T1·T3 기록 합치기 → `python ops/harness/collect.py --out ops/harness/runs/표.md` → 비교표 → 커밋과 푸시.
5. 8절(읽기, [선택]): `플러그인/`으로 하네스를 플러그인으로 묶고 `claude plugin validate`, `claude plugin details`로 확인한다.

## 실행 상한과 교수 시연

학생이 자기 계정으로 실제 모델을 부르는 것은 하네스 유무 비교 1건(작업 T2의 off와 on, `run_task.sh` 두 번)이다(편성표 §3, 부록 A-12-3). 나머지 비교 건(T1, T3)과 반복 실행은 교수 시연이다. 교수는 실행 기록과 판정, 실험 저장소의 변경(diff)을 `교수/make_bundle.py`로 묶어 키트 저장소의 `Agent_07장/시연기록/`에 올린다. 학생은 직접 실행한 T2를 뺀 T1·T3의 기록을 받아 자기 기록과 함께 집계한다.

```bash
mkdir -p ops/harness/runs
cp -n ~/kits/Agent_07장/시연기록/runs/T[13]-* ops/harness/runs/
python ops/harness/collect.py
```

`시연기록/README.md`에 판, 모델, 기준 커밋과 실행 요약이 있고, `diffs/<실행 ID>.diff`에 실험 저장소에서 기준점(`run-base`) 이후의 변경이 있다. 교수 기록이 아직 없으면 `ops/harness/견본기록/`(예시 데이터)의 T1·T3로 같은 절차를 따르고, 비교표 1절에 그렇게 적는다. 사용량이 모자라 T2를 직접 실행하지 못한 학습자는 교수 기록의 T2를 쓰고 1절에 밝힌다.

## Windows에서 알아 둘 것

- `prepare_runs.sh`는 실험 저장소의 `.venv`를 원래 저장소의 가상 환경에 잇는다. 리눅스·macOS는 심볼릭 링크(`ln -s`), Windows의 Git Bash는 디렉터리 연결(`mklink /J`)을 쓴다. Git Bash의 `ln -s`는 링크 대신 폴더 전체를 복사하기 때문이다. 실험 폴더를 `rm -rf`로 지워도 연결 너머의 원래 가상 환경은 지워지지 않는다(2026-11-17 확인).
- 훅과 점검 스크립트는 가상 환경을 켜지 않은 셸에서 돌므로 파이썬을 스스로 고른다. `.venv/Scripts/python.exe`(Windows)가 있으면 그것을, 없으면 `.venv/bin/python`, 그것도 없으면 PATH의 `python`을 쓴다(부록 A-9-2). Windows에는 `python3`이 없거나 스토어 안내 프로그램일 수 있어 `python`을 먼저 찾는다.
- `.mcp.json`은 서버를 `python`으로 띄운다. Claude Code를 가상 환경을 켠 터미널에서 띄워야 그 환경의 파이썬(`mcp` 패키지가 든 것)이 쓰인다.
- `judge.py`와 `교수/make_bundle.py`의 실험 폴더 기본값은 셸의 `HOME` 아래 `agent-lab/exp`이다(`prepare_runs.sh`와 같은 곳). Windows의 파이썬은 `~`를 `USERPROFILE`로 풀므로, `HOME`이 다른 PC에서도 두 도구가 같은 폴더를 보게 하였다.
- 파이썬 출력을 파이프로 넘길 때 한글이 깨지면 부록 A-4-4의 `PYTHONUTF8=1`을 등록한다.

## 확인한 환경

2026-11-17, Windows 11, Git Bash, Python 3.13.7, git 2.55, Claude Code 2.1.296. 스크래치에 키트 저장소를 흉내 낸 로컬 저장소와 2장까지 마친 `jobprep`을 만들어 0~7절의 명령을 차례로 실행하였다. `check_hooks.sh` 통과 18(약 1분 25초), `harness_check.sh` 조립 전 `통과 24, 실패 1`·조립 뒤 `통과 25, 실패 0`(각 약 1분 10초), `python -m pytest ops/harness/tests` 9 passed, `TASKS=T2 prepare_runs.sh` 실험 저장소 둘과 `.venv` 연결, `judge.py`·`collect.py`, 플러그인 `protect.sh`의 보호 목록 대체, `claude plugin validate`·`plugin details`를 확인하였다. `run_task.sh`는 모델을 부르지 않는 가짜 `claude`로 인자(한글 프롬프트, `--plugin-dir`)와 기록 경로만 확인하였고, 실제 모델로는 실행하지 않았다. macOS에서는 확인하지 못하였다.

## 주의

- `ops/harness/견본기록/`의 `*.jsonl`은 Claude Code 문서의 stream-json 형식을 본떠 만든 **예시 데이터**이다. 시간, 턴, 토큰, 비용은 지어낸 값이다. `*.judge.json`은 손으로 만든 변경을 `judge.py`로 실제 판정한 결과이다.
- 실험 저장소의 `.env`에는 실제 키 대신 표지 값(`canary-7f3a-…`)을 넣는다. 실제 키를 넣지 않는다.
- 이 키트의 `기준산출물/`, `조립/`, `충돌연습/`, `플러그인/`에는 `.claude/` 폴더와 `CLAUDE.md`가 들어 있다. 키트 폴더 안에서 `claude`를 띄우면 그 파일들이 읽힐 수 있으므로, Claude Code는 언제나 저장소 폴더에서 띄운다.
- 교수용 파일(정답 견본, 견본 기록 생성기, 시연 지시, 배포 묶음 도구)은 교수 사본의 `교수/`에 있고 학생 키트에는 없다.
