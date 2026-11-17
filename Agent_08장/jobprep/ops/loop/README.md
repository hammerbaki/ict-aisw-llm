# ops/loop: 무인 루프와 파이프라인

「AI에이전트 기획 및 개발」 8장에서 만든다. 설계의 근거는 `docs/운영/루프설계서.md`에 있다.

| 파일 | 하는 일 |
|---|---|
| `fix_until_green.py` | 테스트가 통과할 때까지 에이전트에게 고치게 하는 루프. 재시도·비용·시간 상한, 보호 경로 검사, git 상태 관리, JSONL 기록, 보고서 |
| `prompt_fix.md` | 루프가 시도마다 채워 넘기는 지시문 틀 |
| `fake_agent.py`, `fake/*.json` | `claude -p` 자리에 끼우는 가짜 에이전트와 시나리오(모델을 부르지 않는다) |
| `digest.sh` | 운영 기록 요약 파이프라인: 수집 → 요약 → 통지 |
| `tests/test_loop.py` | 루프 자체의 테스트. `python -m pytest -q ops/loop/tests` |
| `logs/` | 실행 기록 `<실행 이름>.jsonl`과 시도별 지시문 |
| `reports/` | 사람에게 넘기는 보고서와 운영 요약 |

## 실행

```bash
# 가짜 에이전트로 (비용 없음)
AGENT_CMD="python ops/loop/fake_agent.py" FAKE_SCENARIO=success python ops/loop/fix_until_green.py

# 실제 에이전트로 (Claude Code 로그인 필요, 사용량을 쓴다)
python ops/loop/fix_until_green.py
```

종료 코드: 0 통과, 1 재시도 상한, 2 시작 조건 실패, 3 비용·시간 상한, 4 판정 불가.
