# 검토 연습 변경 묶음

`검토연습.patch`는 jobprep에 「운영 일일 보고 스크립트(`ops/daily_report.py`)와 공고 메모(웹)」를 더하는 변경이다. 이 변경에는 운영 규칙을 어긴 곳이 **다섯 군데** 심어져 있다. 6장의 핵심 실습에서 검토 전담 서브에이전트(`reviewer`)가 이 위반을 찾는지 확인하는 데 쓴다.

- 패치는 별도 브랜치(`review-drill`)에만 적용한다. `main`에 병합하지 않는다.
- 패치 안의 키 문자열(`sk-ant-api03-FAKE-...`)은 실습용 가짜 값이다. 실제 키가 아니다.
- 위반의 목록과 위치는 판정 기록을 마친 뒤 교수가 공개한다.

## 적용

저장소 폴더(`~/agent-lab/jobprep`)에서 실행한다. 커밋하지 않은 변경이 없어야 한다(`git status --short`에 `M`이나 `A`로 시작하는 줄이 없어야 한다. `??`로 시작하는 새 파일은 괜찮다).

```bash
git switch -c review-drill
git apply --3way ~/kits/Agent_06장/검토연습/검토연습.patch
git status --short
git commit -m "feat(ops): 운영 일일 보고와 공고 메모(검토 연습, 위반을 심은 변경)"
```

`--3way`는 앞 장에서 같은 파일의 다른 곳을 고쳤더라도 3방향 병합으로 적용한다. 그래도 충돌이 나면 `git apply --3way --reject` 대신 교수에게 알린다.

## 검토 대상 만들기

```bash
mkdir -p .review
echo ".review/" >> .git/info/exclude
git diff main...review-drill > .review/target.diff
```

## 끝낸 뒤

```bash
git switch main
git branch -D review-drill
```
