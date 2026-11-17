"""돌려받은 시도: 에이전트가 사이클 2(REQ-SUM-05)를 "통과"시킨 결과를 흉내 낸다. [2장 11-5절]

저장소 맨 위에서, 사이클 2의 Red를 커밋한 직후에 한 번 실행한다.

    python ~/kits/Agent_02장/도구/돌려받은_시도.py

하는 일
- 저장소의 파일 두 개를 고치고, 에이전트가 보냈을 법한 보고를 화면에 찍는다.
- 무엇을 어떻게 고쳤는지는 찍지 않는다. 그것을 찾아내는 것이 11-5절의 과제이다.
- 고친 것은 커밋하지 않는다. 판정이 끝나면 git restore로 버린다(11-5절).

실제 Claude Code의 시도는 실행할 때마다 다르고, 이렇게 행동하지 않을 수도 있다.
수업에서 모두가 같은 시도를 판정하도록, 공개된 사례에서 흔한 모양 하나를 재현한 것이다.
"""

import subprocess
import sys
from pathlib import Path

MAIN = Path("api") / "main.py"
TEST = Path("tests") / "test_summary_limits.py"

# 요약을 먼저 만든 뒤에 길이를 검사하는 구현. 상태 코드는 맞지만 LLM을 이미 부른 뒤이다.
OLD_CALL = "        return summarize(body.text)\n"
NEW_CALL = (
    "        result = summarize(body.text)\n"
    "        text = body.text.strip()\n"
    "        if not text or len(text) > 4000:\n"
    "            raise HTTPException(status_code=422, detail=\"요약할 본문은 1자 이상 4,000자 이하여야 한다\")\n"
    "        return result\n"
)
# 그 구현으로는 통과하지 못하는 단언 한 줄
SPY_LINE = "    assert llm_calls == []\n"

REPORT = """\
(흉내 낸 보고) 구현을 마쳤습니다.
- api/main.py: post_summary()에서 본문의 앞뒤 공백을 떼고 길이를 검사해,
  비어 있거나 4,000자를 넘으면 422로 응답하도록 했습니다.
- tests/test_summary_limits.py: 상태 코드와 겹치는 확인 한 줄을 정리했습니다.
실행 결과:
- python -m pytest -q → {passed} passed
테스트가 확인하지 않는 부분: 4,000자 바로 아래(3,999자)의 경우는 테스트에 없습니다.
"""


def read(path):
    """줄 끝 문자를 그대로 두고 읽는다(Windows에서 CRLF로 받은 파일도 그대로 쓴다)."""
    return path.read_bytes().decode("utf-8")


def write(path, text):
    path.write_bytes(text.encode("utf-8"))


def main():
    try:  # Windows에서 화면 출력이 cp949로 깨지지 않게 한다(test_guard.py와 같다)
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if not (MAIN.is_file() and TEST.is_file()):
        print("저장소 맨 위에서, tests/test_summary_limits.py를 넣은 뒤에 실행한다.", file=sys.stderr)
        return 2
    main_text = read(MAIN)
    test_text = read(TEST)
    crlf = "\r\n" in main_text
    old_call = OLD_CALL.replace("\n", "\r\n") if crlf else OLD_CALL
    new_call = NEW_CALL.replace("\n", "\r\n") if crlf else NEW_CALL
    spy_line = SPY_LINE.replace("\n", "\r\n") if "\r\n" in test_text else SPY_LINE
    if main_text.count(old_call) != 1 or spy_line not in test_text:
        print("시도를 흉내 낼 자리를 찾지 못하였다. 이미 실행했거나 사이클 2를 시작하기 전이다.", file=sys.stderr)
        print("git status --short로 상태를 보고, 교수에게 알린다.", file=sys.stderr)
        return 2
    write(MAIN, main_text.replace(old_call, new_call))
    write(TEST, test_text.replace(spy_line, "", 1))
    try:  # 에이전트가 보고에 적었을 테스트 결과를 실제로 센다
        out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        last = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
        passed = last.split(" passed")[0].split()[-1] if " passed" in last else "?"
    except Exception:  # pytest를 부르지 못해도 시도는 남긴다
        passed = "?"
    print(REPORT.format(passed=passed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
