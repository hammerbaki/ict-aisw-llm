"""실행 한 건을 판정한다: 인수 검사, 전체 테스트, 규칙 검사.

사용: python ops/harness/judge.py <실행 ID> [--exp ~/agent-lab/exp] [--out ops/harness/runs]
실행 ID는 「작업-조건-반복」 꼴이다(예: T1-on-1). 실험 저장소는 <exp>/<실행 ID>이다.
결과는 <out>/<실행 ID>.judge.json에 쓰고 요약을 한 줄 출력한다.

- T1, T3: 인수검사/test_t?_*.py를 실험 저장소의 tests/에 잠시 복사해 돌리고 지운다.
- T2: 인수검사/check_t2_report.py로 보고서를 검사한다.
- 전체 테스트는 인수 검사 파일을 지운 뒤 실험 저장소에서 pytest -q로 돌린다.
- 테스트에 쓰는 파이썬: 환경 변수 JOBPREP_PYTHON, 없으면 이 도구를 실행한 파이썬.
- 실험 폴더의 기본값은 셸의 HOME 아래 agent-lab/exp이다(prepare_runs.sh와 같은 곳). Windows의 파이썬은 「~」를
  USERPROFILE로 풀므로, HOME이 다른 PC(학교 PC의 네트워크 홈 등)에서도 두 도구가 같은 폴더를 보게 한다.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "인수검사"))

import check_rules  # noqa: E402
import check_t2_report  # noqa: E402

ACCEPTANCE = {"T1": "test_t1_employment_type.py", "T3": "test_t3_ask_log.py"}
RUN_ID = re.compile(r"^(T\d)-(on|off)-(\d+)$")


def pytest(repo, *args):
    python = os.environ.get("JOBPREP_PYTHON", sys.executable)
    result = subprocess.run([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
                            cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    return result.returncode, (lines[-1] if lines else result.stderr.strip()[-200:])


def counts(summary):
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", summary)) else 0
    failed = sum(int(n) for n in re.findall(r"(\d+) (?:failed|error)", summary))
    return passed, failed


def judge(run_id, exp):
    match = RUN_ID.match(run_id)
    if not match:
        raise SystemExit(f"실행 ID 형식이 아니다: {run_id} (예: T1-on-1)")
    task, cond, rep = match.group(1), match.group(2), int(match.group(3))
    repo = Path(exp) / run_id
    if not repo.exists():
        raise SystemExit(f"실험 저장소가 없다: {repo}")
    result = {"run_id": run_id, "task": task, "cond": cond, "rep": rep}

    if task in ACCEPTANCE:
        target = repo / "tests" / f"_accept_{ACCEPTANCE[task]}"
        shutil.copy(HERE / "인수검사" / ACCEPTANCE[task], target)
        try:
            _, summary = pytest(repo, str(target.relative_to(repo)))
        finally:
            target.unlink(missing_ok=True)
        passed, failed = counts(summary)
        result["accept"] = {"passed": passed, "total": passed + failed, "summary": summary}
    else:
        report = check_t2_report.check(repo)
        result["accept"] = {"passed": report["passed"], "total": report["total"],
                            "summary": f"보고서 {report['passed']}/{report['total']}", "items": report["items"]}

    code, summary = pytest(repo)
    result["suite"] = {"ok": code == 0, "summary": summary}
    result["violations"] = check_rules.check(repo)
    return result


def main():
    parser = argparse.ArgumentParser(description="하네스 비교 실험의 실행 한 건을 판정한다")
    parser.add_argument("run_id")
    parser.add_argument("--exp", default=str(Path(os.environ.get("HOME") or Path.home()) / "agent-lab" / "exp"))
    parser.add_argument("--out", default=str(HERE / "runs"))
    for stream in (sys.stdout, sys.stderr):   # Windows에서도 한글 출력을 UTF-8로(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    args = parser.parse_args()
    result = judge(args.run_id, args.exp)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (out / f"{args.run_id}.judge.json").write_bytes(text.encode("utf-8"))  # 줄 끝을 LF로 고정한다
    accept = result["accept"]
    print(f"{args.run_id}: 인수 {accept['passed']}/{accept['total']}, "
          f"전체 테스트 {'통과' if result['suite']['ok'] else '실패'} ({result['suite']['summary']}), "
          f"규칙 위반 {len(result['violations'])}건")


if __name__ == "__main__":
    main()
