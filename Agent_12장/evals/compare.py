"""두 평가 실행의 결과를 나란히 비교한다(판본 비교, 모델 비교).

사용법
    python -m evals.compare evals/runs/<기준 실행> evals/runs/<비교 실행> [--suite summary]

같은 골든 세트를 두 조건으로 돌린 결과를 받아 기준별 통과율, 회귀 통과율, 문항별 차이를 보인다.
두 실행은 같은 문항을 쓰므로 문항마다 차이(비교 - 기준)를 내어 그 평균과 표준오차를 구한다
(짝지은 차이. 두 통과율을 따로 구해 빼는 것보다 오차가 작다).
"""

import argparse
import json
import statistics
import sys
from pathlib import Path


def load(run_dir):
    path = Path(run_dir) / "summary.json"
    if not path.exists():
        raise SystemExit(f"요약 파일이 없다: {path.as_posix()} (먼저 python -m evals.run을 실행한다)")
    return json.loads(path.read_text(encoding="utf-8"))


def label(summary, suite):
    return f"{summary['prompts'][suite]}/{summary['model']}"


def paired_difference(base, other):
    """회귀 문항마다 (비교 통과율 - 기준 통과율)을 내어 평균과 표준오차를 돌려준다."""
    diffs, changed = [], []
    for item_id, info in base["per_item"].items():
        if info["suite"] != "regression" or item_id not in other["per_item"]:
            continue
        a = info["passes"] / info["runs"]
        b = other["per_item"][item_id]["passes"] / other["per_item"][item_id]["runs"]
        diffs.append(b - a)
        if abs(b - a) >= 0.4:
            changed.append((item_id, a, b))
    if not diffs:
        return 0.0, 0.0, changed
    mean = statistics.fmean(diffs)
    sem = statistics.stdev(diffs) / len(diffs) ** 0.5 if len(diffs) > 1 else 0.0
    return mean, sem, changed


def compare(base_dir, other_dir, suites=None):
    base, other = load(base_dir), load(other_dir)
    for suite in suites or base["suites"]:
        if suite not in base["suites"] or suite not in other["suites"]:
            continue
        a, b = base["suites"][suite], other["suites"][suite]
        la, lb = label(base, suite), label(other, suite)
        print(f"[{suite}] 기준 {la} (반복 {base['runs']}) ↔ 비교 {lb} (반복 {other['runs']})")
        print(f"  {'기준':<12}{la:>22}{lb:>22}{'차이':>8}")
        for name in a["criteria"]:
            x, y = a["criteria"][name], b["criteria"].get(name)
            if x is None or y is None:
                print(f"  {name:<12}{'해당 없음':>22}{'해당 없음':>22}")
                continue
            print(f"  {name:<12}{x:>22.2f}{y:>22.2f}{y - x:>+8.2f}")
        print(f"  {'회귀 통과율':<10}{a['pass_rate']:>22.2f}{b['pass_rate']:>22.2f}{b['pass_rate'] - a['pass_rate']:>+8.2f}")
        print(f"  {'모든 반복 통과':<9}{a['pass_all_runs']:>20}/{a['regression_items']}"
              f"{b['pass_all_runs']:>19}/{b['regression_items']}")
        mean, sem, changed = paired_difference(a, b)
        low, high = mean - 1.96 * sem, mean + 1.96 * sem
        print(f"  짝지은 차이: 평균 {mean:+.3f}, 표준오차 {sem:.3f}, 95% 구간 {low:+.3f}~{high:+.3f}")
        if low > 0:
            print("  판단: 비교 쪽이 낫다(구간이 0보다 크다)")
        elif high < 0:
            print("  판단: 비교 쪽이 나쁘다(구간이 0보다 작다)")
        else:
            print("  판단: 차이를 말할 수 없다(구간이 0을 포함한다). 문항이나 반복을 늘려 다시 잰다")
        for item_id, x, y in changed:
            print(f"  크게 바뀐 문항: {item_id} {x:.1f} → {y:.1f}")
        print()


def main(argv=None):
    parser = argparse.ArgumentParser(description="두 평가 실행의 비교")
    parser.add_argument("base")
    parser.add_argument("other")
    parser.add_argument("--suite", choices=["summary", "ask"])
    args = parser.parse_args(argv)
    compare(args.base, args.other, [args.suite] if args.suite else None)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
