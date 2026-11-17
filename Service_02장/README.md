# 2장 실습 키트: 개인 개발 환경 (Claude Code와 Git)

「LLM 서비스 개발」 2장(학사 3주차)의 실습 재료이다. 강의안 `Service_02장_학생용.md`와 함께 쓴다. 내 PC(Windows는 Git Bash, macOS는 터미널)에서 쓴다.

## 받기

```bash
git -C ~/kits-repo pull
mkdir -p ~/kits
cp -rn ~/kits-repo/Service_02장 ~/kits/
```

`~/kits-repo`는 1주차에 클론한 수업용 키트 저장소이다(부록 A-12). 키트는 저장소(`~/llm-service-lab`) 밖의 `~/kits/`에 두고, 필요한 파일만 저장소로 복사한다.

## 들어 있는 것

| 경로 | 무엇 | 쓰는 절 |
|---|---|---|
| `기준산출물/ch01/` | 1장 결과가 없는 학습자를 위한 대체 산출물 | 0절 |
| `견본/gitignore_견본.txt` | 저장소 맨 위에 `.gitignore`로 복사할 견본 | 3-3, 3-4 |
| `골격/deadline/` | 핵심 실습의 대상 프로그램(지원 일정 마감 알림)과 테스트 | 4-1, 12절 |
| `견본/CLAUDE_견본.md` | `/init`이 만든 초안과 견줄 CLAUDE.md 견본 | 6절, 12-2 |
| `도구/make_sandbox.sh` | 되돌리기를 연습할 `~/git-sandbox`를 만든다 | 9절(따라 하기 2), [선택] 10절 |
| `작업기록_양식.md` | 핵심 실습의 기록 양식. `ch02/작업기록.md`로 복사해 쓴다 | 12절 |
| `과제지시문.md` | 핵심 실습에서 Claude Code에 보낼 지시 A와 [선택] 지시 B·C, 완료 기준 | 12절 |
| `카드/커밋메시지_규칙카드.md` | 커밋 메시지의 모양과 규칙 | 4-3, 12절 |
| `카드/되돌리기_상황표.md` | 상황별로 쓸 되돌리기 명령 | 8절, 9절, 12절 |
| `도구/check_ch02.py` | 저장소가 2장의 완료 기준을 충족하는지 점검한다 | 12-9 |
| `교수/` | 교수 전용(모범 변경, 재현 스크립트, 정답 기록). 학생용 키트 저장소와 공개 사이트에 올리지 않는다 | |

## 순서

1. 0절: 키트를 받고 `~/llm-service-lab/ch01/`을 확인한다. 없으면 `cp -rn ~/kits/Service_02장/기준산출물/ch01 ~/llm-service-lab/`.
2. 2절: 부록 A-9의 git 설정을 확인하고 `core.editor`를 더한다.
3. 3-4, 4-1(따라 하기 1): 저장소와 가상 환경을 만들고 `ch01/`, `.gitignore`, `ch02/deadline/`을 커밋한다.
4. 9-2(따라 하기 2): `~/git-sandbox`에서 `restore`와 `revert`를 한다.
5. 11-4(따라 하기 3): GitHub에 비공개 저장소를 만들고 푸시한다.
6. 12절(핵심 실습): `과제지시문.md`에 따라 CLAUDE.md, 되감기 시험, 지시 A, diff 읽기, 커밋 셋, 되돌리기, 푸시를 하고 `check_ch02.py`로 점검한다.

## 골격 프로그램의 테스트

가상 환경을 켠 터미널에서 실행한다(Windows `source ~/llm-service-lab/.venv/Scripts/activate`, macOS `source ~/llm-service-lab/.venv/bin/activate`).

```bash
cd ~/llm-service-lab/ch02/deadline
python -m pytest -q          # 4 passed
python deadline.py --today 2027-03-15
```

`requirements.txt`는 `pytest==9.2.0`이다. 가상 환경은 저장소 맨 위의 `~/llm-service-lab/.venv` 하나를 쓴다(부록 A-13). Windows에서 파이썬 출력을 파이프(`|`)로 넘기면 한글이 cp949로 나가 깨진다. 파이프로 넘기지 않는다.

## 완료 점검

```bash
python ~/kits/Service_02장/도구/check_ch02.py ~/llm-service-lab
```

가상 환경을 켠 터미널에서 실행한다(점검기가 테스트를 직접 돌린다). 모든 줄이 `[통과]`이고 마지막 줄이 `20/20 통과`이면 2장의 완료 기준을 충족한다. `[미통과]` 아래의 `→` 줄이 고칠 곳을 알려 준다. 선택 과제(12-10)는 `[선택 · …]`으로 따로 보이고 통과 수에 넣지 않는다.
