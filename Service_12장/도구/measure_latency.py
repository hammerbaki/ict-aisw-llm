"""과업 하나(시나리오)를 여러 번 수행하고 걸린 시간을 잰다.

시나리오 JSON은 사용자가 과업 하나를 끝내기까지 보내는 요청의 순서다. 대화형 단계("say")는
앞 단계의 응답을 대화 이력에 붙여 다음 요청에 함께 보낸다.

    python 도구/measure_latency.py --base http://127.0.0.1:8000 --scenario 시나리오/form.json --repeat 5
    python 도구/measure_latency.py --app-dir ~/llm-service-lab/jobprep --scenario 시나리오/form.json

--base는 실행 중인 서버에, --app-dir는 같은 프로세스 안의 앱에 보낸다(네트워크 시간이 빠진다).
모의 모드의 시간은 LLM_FAKE_LATENCY=on일 때 흉내 낸 값이며 실제 모델의 시간이 아니다.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Client, fill, utf8_stdout  # noqa: E402


def load_inputs(scenario: dict, base_dir: Path) -> dict:
    inputs = {}
    for key, value in scenario.get("inputs", {}).items():
        if key.endswith("_file"):
            inputs[key[: -len("_file")]] = (base_dir / value).read_text(encoding="utf-8").strip()
        else:
            inputs[key] = value
    return inputs


def run_once(client: Client, scenario: dict, inputs: dict) -> list[dict]:
    history: list[dict] = []
    reply_field = scenario.get("reply_field", "reply")
    records = []
    for i, step in enumerate(scenario["steps"], 1):
        body = fill({**scenario.get("base_body", {}), **step.get("body", {})}, inputs)
        if "say" in step:
            history.append({"role": "user", "content": fill(step["say"], inputs)})
            body["messages"] = list(history)
        status, data, ms = client.post(step["path"], body)
        if "say" in step and status == 200:
            history.append({"role": "assistant", "content": str(data.get(reply_field, ""))})
        records.append({"step": i, "status": status, "ms": ms})
    return records


def main() -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--base")
    ap.add_argument("--app-dir")
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=1, help="재지 않고 먼저 돌리는 횟수")
    ap.add_argument("--out", help="결과를 CSV로 저장할 경로")
    args = ap.parse_args()

    path = Path(args.scenario)
    scenario = json.loads(path.read_text(encoding="utf-8"))
    inputs = load_inputs(scenario, path.parent)
    client = Client(base=args.base, app_dir=args.app_dir)

    for _ in range(args.warmup):
        run_once(client, scenario, inputs)
    runs = [run_once(client, scenario, inputs) for _ in range(args.repeat)]

    errors = sum(1 for run in runs for r in run if r["status"] != 200)
    totals = [sum(r["ms"] for r in run) for run in runs]
    print(f"시나리오: {scenario['name']} · 과업당 요청 {len(scenario['steps'])}회 · 반복 {args.repeat}회 (준비 {args.warmup}회 제외)")
    for i in range(len(scenario["steps"])):
        step_ms = [run[i]["ms"] for run in runs]
        print(f"  단계 {i + 1}: 중앙값 {statistics.median(step_ms):8.1f} ms")
    print(f"과업 시간: 중앙값 {statistics.median(totals):.1f} ms · 최소 {min(totals):.1f} · 최대 {max(totals):.1f}")
    print(f"200이 아닌 응답: {errors}건")
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["run", "step", "status", "ms"])
            for n, run in enumerate(runs, 1):
                for r in run:
                    w.writerow([n, r["step"], r["status"], f"{r['ms']:.1f}"])
        print(f"저장: {args.out}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
