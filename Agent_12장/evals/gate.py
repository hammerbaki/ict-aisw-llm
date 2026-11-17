"""회귀 판정: 평가 결과가 합격선과 기준선을 지키는지 보고 종료 코드로 알린다.

사용법
    python -m evals.gate evals/runs/<실행>                  판정만 한다
    python -m evals.gate evals/runs/<실행> --update-baseline 판정을 통과하면 이 결과를 기준선으로 적는다

종료 코드
    0  합격: 모든 합격선을 넘고, 기준선보다 허용 폭 넘게 떨어지지 않았다
    1  회귀: 합격선 미달 또는 기준선 대비 하락. 13장의 CI는 이 코드로 병합을 막는다
    2  사용 오류: 파일이 없거나 형식이 맞지 않다

합격선은 evals/thresholds.json, 기준선은 evals/baseline.json에 둔다. 두 파일은 저장소에 커밋한다.
판정은 회귀 문항(suite가 regression인 문항)만으로 한다. 능력 문항은 보고만 한다.
"""

import argparse
import json
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
THRESHOLDS = EVALS_DIR / "thresholds.json"
BASELINE = EVALS_DIR / "baseline.json"


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"파일이 없다: {Path(path).as_posix()}")
        sys.exit(2)
    except json.JSONDecodeError as error:
        print(f"JSON 형식 오류: {Path(path).as_posix()} ({error.msg})")
        sys.exit(2)


def check(summary, thresholds, baseline):
    """판정 결과 줄의 목록과 합격 여부를 돌려준다."""
    lines, ok = [], True
    max_drop = thresholds.get("max_drop_from_baseline", 0.05)
    for suite, result in summary["suites"].items():
        rule = thresholds.get(suite)
        if rule is None:
            lines.append(f"  [건너뜀] {suite}: 합격선이 없다")
            continue
        value = result["pass_rate"]
        passed = value >= rule["min_pass_rate"]
        ok &= passed
        lines.append(f"  [{'통과' if passed else '실패'}] {suite} 회귀 통과율 {value:.2f} (합격선 {rule['min_pass_rate']:.2f})")
        for name, minimum in rule.get("min_criteria", {}).items():
            actual = result["criteria"].get(name)
            if actual is None:
                lines.append(f"  [실패] {suite}.{name}: 결과에 이 기준이 없다")
                ok = False
                continue
            passed = actual >= minimum
            ok &= passed
            lines.append(f"  [{'통과' if passed else '실패'}] {suite}.{name} {actual:.2f} (합격선 {minimum:.2f})")
        if baseline and suite in baseline.get("suites", {}):
            before = baseline["suites"][suite]["pass_rate"]
            passed = value >= before - max_drop
            ok &= passed
            lines.append(f"  [{'통과' if passed else '실패'}] {suite} 기준선 대비 {value - before:+.2f}"
                         f" (기준선 {before:.2f}, 허용 하락 {max_drop:.2f})")
    return lines, ok


def main(argv=None):
    parser = argparse.ArgumentParser(description="회귀 판정")
    parser.add_argument("run_dir")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args(argv)

    summary = read_json(Path(args.run_dir) / "summary.json")
    thresholds = read_json(THRESHOLDS)
    baseline = read_json(BASELINE) if BASELINE.exists() else None
    if summary.get("runs", 0) < thresholds.get("min_runs", 1):
        print(f"반복 횟수 {summary.get('runs')}회는 판정에 모자란다(최소 {thresholds['min_runs']}회)")
        return 2

    print(f"회귀 판정: {summary['tag']} (모델 {summary['model']}, 반복 {summary['runs']}회)")
    if baseline is None:
        print("  기준선 없음: 합격선만 본다")
    lines, ok = check(summary, thresholds, baseline)
    print("\n".join(lines))
    print("결과: 합격" if ok else "결과: 회귀(종료 코드 1)")
    if ok and args.update_baseline:
        record = {"tag": summary["tag"], "created": summary["created"], "model": summary["model"],
                  "prompts": summary["prompts"], "runs": summary["runs"],
                  "suites": {s: {"pass_rate": r["pass_rate"], "criteria": r["criteria"]}
                             for s, r in summary["suites"].items()}}
        BASELINE.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"기준선을 적었다: evals/{BASELINE.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
