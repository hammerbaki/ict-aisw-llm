# 12장 키트: 평가와 관측

「AI에이전트 기획 및 개발」 12장(학사 14주차)의 실습 재료이다. `jobprep`의 요약·질의응답 기능에 회귀 평가를 두고, 판본 비교 한 번으로 회귀를 찾아 고친 뒤 회귀 판정기로 승인하며, 서비스 기록과 에이전트 실행 기록에서 성공률과 비용을 보고한다. 모든 실습은 API 키 없이 모의 모델로 끝까지 돈다.

## 받는 법

키트 저장소(`~/kits-repo`)에서 저장소 밖의 `~/kits/`로 받는다(부록 A-7-3).

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Agent_12장 ~/kits/
```

## 들어 있는 것

| 경로 | 저장소로 옮기는 곳 | 쓰는 절 | 내용 |
|---|---|---|---|
| `기준산출물/ops/loop/logs/` | `ops/loop/logs/` | 0-2, 7-3, 11-6 | 8장 루프 실행 기록(JSON Lines) 견본 7건. 8장을 마친 학습자는 자기 기록을 쓴다 |
| `기준산출물/ops/multi/logs/` | `ops/multi/logs/` | 0-2, 7-3, 11-6 | 10장 멀티 에이전트 실행 기록 견본 3건(이슈마다 `events.jsonl`과 에이전트 출력) |
| `evals/` | `evals/` | 2-6, 3-3, 11절 | 골든 세트(요약 15, 질의응답 10. 회귀 23, 능력 2), 채점기, 변동 모의 모델, 판정자, 실행기, 비교, 회귀 판정, 판정자 보정, 테스트 |
| `ops/telemetry/` | `ops/telemetry/` | 2-6, 11-6 | 기록 읽기, 관측 보고(지표, 비용, 예산), 개인 정보 점검, 가격표, 테스트 |
| `재료/test_preferred.py` | `evals/tests/` | 11-2 | 학습자가 만드는 채점기 `grade_preferred`의 테스트(먼저 실패한다) |
| `평가보고_양식.md` | `docs/운영/평가보고.md` | 11-7 | 평가 보고의 양식 |
| `시연기록/` | `evals/runs/`(필요한 실행 폴더만) | 11-9 | 교수 시연(실제 모델 평가)의 실행 기록. 수업 중에 키트 저장소로 올라온다 |

## 순서

모든 명령은 가상 환경을 켠 터미널에서, 저장소 맨 위(`~/agent-lab/jobprep`)에서 실행한다.

```bash
cd ~/agent-lab/jobprep
source .venv/Scripts/activate            # macOS: source .venv/bin/activate
cp -rn ~/kits/Agent_12장/evals/. evals/
mkdir -p ops/telemetry && cp -rn ~/kits/Agent_12장/ops/telemetry/. ops/telemetry/
echo "evals/runs/" >> .gitignore
python -m pytest -q evals ops/telemetry | tail -1      # 33 passed
```

| 명령 | 하는 일 |
|---|---|
| `python -m evals.run --suite summary --prompt summary_v1 --runs 5` | 요약 골든 세트를 5번 돌려 채점한다(모의 모델, 1~2초) |
| `python -m evals.compare evals/runs/A evals/runs/B` | 두 실행을 기준별로 비교하고 짝지은 차이를 낸다 |
| `python -m evals.gate evals/runs/A [--update-baseline]` | 합격선과 기준선으로 회귀를 판정한다(종료 코드 0, 1, 2) |
| `python -m evals.calibrate [--numbers]` | 판정자와 사람 표본의 일치도(카파)를 잰다(교수 시연) |
| `python -m evals.judge pairwise-demo` | 위치 편향과 순서 바꾸기 점검을 보인다(교수 시연) |
| `python -m ops.telemetry.report [--budget-usd 5] [--out 파일]` | 서비스·LLM·루프·멀티 에이전트 기록을 모아 보고한다 |
| `python -m ops.telemetry.pii_scan logs ops evals/runs` | 기록에 개인 정보 꼴이 있는지 본다 |

`evals`와 `ops.telemetry`의 명령은 Windows의 Git Bash에서 파이프(`| grep`, `| sed`)로 넘겨도 한글이 깨지지 않게 표준 출력을 UTF-8로 내보낸다. 강의안에서 직접 쓰는 `python -c` 한 줄 명령의 출력을 파이프로 넘길 때는 부록 A-4-4의 `PYTHONUTF8=1`을 따른다.

## 변동 모의 모델에 대하여

`--backend sim`(기본)은 `evals/sim.py`의 교육용 모의 모델을 쓴다. 기준 저장소의 모의 응답에 판본(프롬프트의 규칙 문장)에 따라 달라지는 실수와, 반복 번호에 따라 달라지는 결정적 잡음을 더한 것이다. API를 부르지 않으며, 같은 조건이면 어느 컴퓨터에서나 같은 점수가 나온다. 모의 모델의 확률은 집필자가 정한 값이므로, 그 점수로 실제 모델의 품질을 말할 수 없다.

## 실제 모델(선택, 한 번)

`--backend real`은 실제 모델을 부르고 비용이 든다. 셸 환경 변수나 저장소 맨 위의 `.env`에서 `ANTHROPIC_API_KEY`와 `LLM_MODEL`을 읽고(셸의 값이 앞선다), 키가 없으면 모델을 부르기 전에 멈춘다. 학생의 실행 상한은 한 번이다(편성표 §3, 부록 A-12-3).

```bash
python -m evals.run --suite all --prompt summary_v3 --runs 1 --backend real --tag real-mine   # 약 50회 호출
```

평가는 `.env`의 `EMBED_BACKEND`와 관계없이 대체 임베딩(fallback)으로 고정한다(판본 비교의 조건 통제).

## 확인한 환경

2026-11-17, Windows 11의 Git Bash, Python 3.13.7, 1장 기준 저장소의 `requirements.txt`(pytest 9.2.0 등). 키트 저장소를 흉내 낸 로컬 저장소에서 받아 강의안의 명령을 차례로 실행하였다(학생 키트는 `교수/` 제외). 실제 모델과 macOS는 확인하지 못하였다.
