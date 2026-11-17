"""가짜 테스트 에이전트: ISSUE-07의 인수 테스트를 tests/에 놓고, 지금은 실패하는지(Red) 확인한다.

실제 수업에서는 Claude Code의 tester 에이전트가 계획서의 계약에서 인수 테스트를 쓴다(6절).
이 스크립트는 같은 결과물을 모델 없이 만드는 대역이다. 커밋하지 않는다.

사용법 (저장소 맨 위에서, 통합 브랜치에 있는 상태로)
    python ops/multi/fake/test_agent.py
종료 코드: 새 테스트가 모두 실패하면(Red) 0, 하나라도 통과하면 1(테스트가 아무것도 재지 않는다).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
SOURCE = Path(__file__).resolve().parent / "answers" / "tests"


def main():
    new_tests = []
    for path in sorted(SOURCE.glob("test_*.py")):
        dest = ROOT / "tests" / path.name
        if dest.exists():
            print(f"있음  tests/{path.name} (덮어쓰지 않는다)")
        else:
            shutil.copyfile(path, dest)
            print(f"씀    tests/{path.name}")
        new_tests.append(f"tests/{path.name}")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", *new_tests],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    last = [line for line in result.stdout.splitlines() if line.strip()][-1]
    print(f"Red 확인: {last}")
    if re.search(r"\d+ passed", last):
        print("경고: 구현 전인데 통과하는 테스트가 있다. 그 테스트는 요구를 재지 못한다")
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
