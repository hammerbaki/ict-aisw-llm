# 12장 키트: 비교 구현

「LLM 서비스 개발」 12장(학사 14주차)의 실습 재료이다. 강의안은 `Service_12장_학생용.md`이다. 서비스 5의 뒤 절반으로, 11장의 기능 명세와 화면 명세로 구현 둘(`variant-a`, `variant-b`)을 Orca의 작업 공간 두 개에서 만들고, 기준표로 견주어 하나를 고르고, 두 구현이 다르게 정한 곳을 명세에 보강한다.

## 받는 법

```bash
git -C ~/kits-repo pull && cp -rn ~/kits-repo/Service_12장 ~/kits/
source ~/llm-service-lab/.venv/Scripts/activate      # macOS: source ~/llm-service-lab/.venv/bin/activate
cd ~/kits/Service_12장
python -m pip install -r requirements.txt
python -m pytest -q                                  # 4 passed
```

## 들어 있는 것

| 경로 | 쓰는 절 | 내용 |
|---|---|---|
| `변형지시_공통_양식.md` | 4-2, 8-2 | 두 세션에 똑같이 주는 지시(기준 문서, 할 일, 계약, 하지 말 것, 보고). `ch12/변형지시/공통.md`로 복사한다 |
| `변형지시_변형_양식.md` | 4-2, 8-2 | 변형의 축 하나만 적는 지시의 예. `a.md`, `b.md`로 쓴다 |
| `비교구현_양식.md` | 5절, 8-2~8-6 | 비교 조건, 기준표, 휴리스틱 위반, 스스로 정한 것, 다르게 정한 곳. `ch12/비교구현.md`로 복사한다 |
| `명세점검표_양식.md` | 5-2, 8-5 | 변형마다 하나. `ch12/점검표_a.md`, `점검표_b.md`로 복사한다 |
| `결정기록_양식.md` | 6절, 8-7 | ADR. `ch12/결정기록.md`로 복사한다 |
| `연습/점검표_A.md` | 5-2 | 집계 도구를 익히는 작은 점검표(충족률 75.0%) |
| `도구/spec_checklist.py` | 5-2, 8-5 | 점검표의 판정을 세어 충족률을 낸다. 충족률 = (충족 + 0.5 × 부분) ÷ (전체 − 해당없음) |
| `tests/` | 0절 | 도구의 테스트 |
| `교수/` | 교수용 | 견본 구현 둘, 견본 점검표와 기준표와 ADR, 시연 저장소 스크립트. 학생 키트 저장소에 넣지 않는다 |

HTML 점검과 대비 점검은 11장 키트의 `~/kits/Service_11장/tools/`를 그대로 쓴다.

## 쓰는 순서

```bash
KIT=~/kits/Service_12장
cd ~/llm-service-lab
mkdir -p ch12/변형지시
cp ch11/기능명세.md ch11/화면명세.md ch12/
cp -n "$KIT"/비교구현_양식.md ch12/비교구현.md
cp -n "$KIT"/결정기록_양식.md ch12/결정기록.md
cp -n "$KIT"/변형지시_공통_양식.md ch12/변형지시/공통.md
cp -n "$KIT"/명세점검표_양식.md ch12/점검표_a.md
cp -n "$KIT"/명세점검표_양식.md ch12/점검표_b.md
# 구현과 점검 뒤
python "$KIT/도구/spec_checklist.py" ch12/점검표_a.md ch12/점검표_b.md
```

판정 칸에 정해진 말(충족, 부분, 미충족, 해당없음)이 아닌 것을 쓰면 도구가 그 줄을 「판정을 읽지 못함」으로 알리고 종료 코드 1로 끝난다.

## 확인한 환경

2026-11-18, Windows 11(빌드 26300)의 Git Bash, git 2.55.0.windows.5, Python 3.13.7 가상 환경(pytest 9.2.0)에서 `python -m pytest -q`(4 passed)와 위 명령을 실행하였다. 핵심 실습의 git 흐름은 `교수/시연_저장소_만들기.sh`로 견본 구현을 써서 끝까지 실행하였다. Orca의 화면과 Claude Code 두 세션의 구현은 실행하지 않았다(교수 리허설). macOS에서는 실행하지 않았다.
