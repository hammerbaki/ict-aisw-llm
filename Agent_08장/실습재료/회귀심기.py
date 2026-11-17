"""회귀 두 건을 api/jobs.py에 심는다(8장 중심 실습의 출발점).

`git apply 회귀두건.patch`가 앞 장에서 바뀐 코드 때문에 적용되지 않을 때 쓴다.
저장소 맨 위에서 실행한다: python ~/kits/Agent_08장/실습재료/회귀심기.py
"""

import sys
from pathlib import Path

TARGET = Path("api/jobs.py")
CHANGES = [
    ("    return (deadline - today()).days", "    return (today() - deadline).days"),
    ('    result.sort(key=lambda item: item["deadline"])', '    result.sort(key=lambda item: item["deadline"], reverse=True)'),
]


def main():
    if not TARGET.exists():
        print("api/jobs.py가 없다. 저장소 맨 위(jobprep/)에서 실행한다.")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    for old, new in CHANGES:
        if old not in text:
            print(f"바꿀 줄을 찾지 못하였다: {old.strip()}")
            return 1
        text = text.replace(old, new, 1)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print("api/jobs.py에 회귀 두 건을 심었다: 남은 날 수의 부호, 목록의 정렬 방향")
    return 0


if __name__ == "__main__":
    sys.exit(main())
