"""비밀 정보 검사의 입구. 13장의 CI가 `python security/scan_secrets.py`로 부른다.

검사 본체는 security/tools/scan_secrets.py이다(11장). 인자는 그대로 넘긴다.
종료 코드: 커밋될 수 있는 파일에서 비밀로 보이는 값을 찾으면 1, 없으면 0.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from scan_secrets import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
