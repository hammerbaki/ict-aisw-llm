# 시연기록: 실제 호출로 다시 잰 기록 (교수 시연)

이 폴더에는 교수가 수업 전에 교수 시연 저장소의 두 변형(양식형, 대화형)을 실제 모델로 잰 기록이 들어간다. 강의안 5-10절에서 쓴다.

| 파일 | 내용 |
|---|---|
| `llm_calls_form.jsonl`, `llm_calls_chat.jsonl` | 호출 기록. 한 줄에 호출 하나(시각, 변형, 용도, 토큰 수, 걸린 시간). 입력한 답변은 없다(REQ-087) |
| `시간_form.csv`, `시간_chat.csv` | `measure_latency.py --warmup 0 --repeat 3`의 결과 |
| `요약.md` | 생성 방식(실제 호출 또는 모의 모드), 단가, 과업 시간, 집계표 |

같은 과업을 실제 모델로 되풀이해 재는 것은 이 장의 실행 상한을 넘으므로 교수 시연으로 한다. 이 장은 모의 모드로 끝까지 할 수 있으며, 각자 Console 키를 발급한 학생도 반복 측정은 하지 않는다.

```bash
cd ~/kits/Service_12장
python 도구/token_report.py 시연기록/llm_calls_form.jsonl 시연기록/llm_calls_chat.jsonl --tasks 3 --price-in 1.0 --price-out 5.0
```

기록은 교수 견본 구현으로 잰 것이므로 숫자가 자기 구현과 다르다. 두 변형의 순위가 모의 모드의 기준표와 같은지만 견준다. `요약.md`의 「생성」 줄이 「모의 모드」이면 키 없이 만든 점검용 기록이므로 실제 값으로 쓰지 않는다.

수업 전에 기록이 올라오지 않았으면 이 안내 파일만 있다. 기록은 수업 중에 다시 받는다.

```bash
git -C ~/kits-repo pull
cp -rn ~/kits-repo/Service_12장/시연기록 ~/kits/Service_12장/
```
