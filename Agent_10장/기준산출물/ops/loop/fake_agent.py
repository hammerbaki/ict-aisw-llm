"""가짜 에이전트: `claude -p` 자리에 끼워 루프를 모델 없이 돌리는 테스트 더블.

시나리오 파일(JSON)에 시도마다 할 일을 적어 둔다. 가짜 에이전트는 환경 변수 LOOP_ATTEMPT(루프가 넣는다)로
몇 번째 시도인지 알고, 그 시도의 편집을 파일에 적용한 뒤 `claude -p --output-format json`과
같은 모양의 결과 객체를 표준 출력에 한 줄로 낸다. 모델을 부르지 않으므로 비용은 시나리오에 적힌 값이다.

사용법
    FAKE_SCENARIO=success python ops/loop/fake_agent.py -p "지시문" --output-format json
    FAKE_SCENARIO는 이름(ops/loop/fake/<이름>.json) 또는 시나리오 파일의 경로이다.

시나리오 파일의 모양
    {"attempts": [ {"edits": [{"file": "api/jobs.py", "old": "...", "new": "..."}],
                    "cost_usd": 0.18, "turns": 6, "result": "...\\nOK"}, ... ]}
    시도 항목의 선택 키: "subtype"(예: "error_max_turns"), "sleep_s"(시간 끌기),
    "reads_stdin": true(표준 입력의 줄 수를 결과의 {lines} 자리에 넣는다), "overshoot_usd".
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_scenario(name):
    path = Path(name)
    if not path.suffix:
        path = HERE / "fake" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")), path.stem


def apply_edits(edits):
    """old를 new로 한 번 바꾼다. old가 없으면 그 편집은 실패로 센다."""
    missed = []
    for edit in edits:
        target = Path(edit["file"])
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        if edit.get("old", "") == "" and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(edit["new"], encoding="utf-8", newline="\n")
        elif edit["old"] in text:
            target.write_text(text.replace(edit["old"], edit["new"], 1), encoding="utf-8", newline="\n")
        else:
            missed.append(edit["file"])
    return missed


def main():
    for stream in (sys.stdout, sys.stdin):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-p", "--print", dest="prompt", nargs="?", const="")
    parser.add_argument("--output-format", default="text")
    parser.add_argument("--max-budget-usd", type=float)
    parser.add_argument("--max-turns", type=int)
    args, _ = parser.parse_known_args()  # 나머지 옵션(--allowedTools 등)은 받아 두고 쓰지 않는다

    scenario, name = load_scenario(os.environ.get("FAKE_SCENARIO", "success"))
    attempt = int(os.environ.get("LOOP_ATTEMPT", "1"))
    steps = scenario.get("attempts", [])
    step = steps[attempt - 1] if attempt <= len(steps) else {"result": "더 할 일이 없다.\nFAIL"}

    time.sleep(step.get("sleep_s", 0))
    cost = float(step.get("cost_usd", 0.05))
    turns = int(step.get("turns", 3))
    out = {"type": "result", "subtype": "success", "is_error": False,
           "duration_ms": int(step.get("sleep_s", 0) * 1000) + 1200, "num_turns": turns,
           "session_id": f"fake-{name}-{attempt}", "total_cost_usd": cost,
           "usage": {"input_tokens": 1000 * turns, "output_tokens": 150 * turns}}

    if args.max_budget_usd is not None and cost > args.max_budget_usd:
        # 시도 한 번의 비용 상한에 닿았다. 응답 하나만큼 상한을 넘을 수 있다(문서의 budget headroom).
        out.update(subtype="error_max_budget_usd", is_error=True,
                   total_cost_usd=round(args.max_budget_usd + step.get("overshoot_usd", 0.03), 4))
    elif args.max_turns is not None and turns > args.max_turns:
        out.update(subtype="error_max_turns", is_error=True, num_turns=args.max_turns)
    elif step.get("subtype", "success") != "success":
        out.update(subtype=step["subtype"], is_error=True)
    else:
        missed = apply_edits(step.get("edits", []))
        text = step.get("result", "OK")
        if step.get("reads_stdin"):
            lines = [] if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read().splitlines()
            text = text.replace("{lines}", str(len([line for line in lines if line.strip()])))
        if missed:
            text += f"\n(편집 대상을 찾지 못함: {', '.join(missed)})"
        out["result"] = text

    if args.output_format == "json":
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(out.get("result", f"Error: {out['subtype']}"))
    return 1 if out["is_error"] else 0


if __name__ == "__main__":
    sys.exit(main())
