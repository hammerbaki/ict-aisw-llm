"""재현성을 위해 고정해야 할 버전이 모두 고정되어 있는지 검사한다 (13장).

검사 항목
  P1  워크플로의 모든 외부 액션(uses:)이 40자리 커밋 SHA로 고정되어 있고, 사람이 읽을 판 번호 주석(# vX.Y.Z)이 붙어 있다
  P2  requirements.lock이 있고, 모든 패키지가 ==로 고정되고 --hash가 붙어 있으며,
      requirements.txt에서 ==로 고정한 직접 의존성이 잠금 파일에도 같은 판으로 있다
  P3  .python-version이 있고, 워크플로의 setup-python이 그 파일을 읽는다(python-version-file)
  P4  .env.example의 LLM_MODEL이 비어 있지 않고, 별칭(-latest)이 아닌 모델 이름이다
  P5  .env.example이 프롬프트 판본(PROMPT_SUMMARY, PROMPT_ASK)을 명시한다

쓰는 법 (저장소 폴더에서)
    python ops/version/check_pins.py
고정되지 않은 것이 하나라도 있으면 종료 코드 1이다. 표준 라이브러리만 쓴다.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)\s*(#.*)?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"#\s*v\d+(?:\.\d+){0,2}\b")
REQ_PIN = re.compile(r"^([A-Za-z0-9_.\-\[\]]+)==([^\s;\\]+)")
LOCK_LINE = re.compile(r"^([A-Za-z0-9_.\-]+)==(\S+)\s*\\?$")


def normalize(name):
    return re.sub(r"[-_.]+", "-", name.split("[")[0]).lower()


def check_actions(problems):
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not files:
        problems.append(("P1", ".github/workflows/", "워크플로가 없다"))
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            found = USES.match(line)
            if not found:
                continue
            ref = found.group(1)
            if ref.startswith(("./", "$/", "docker://")):
                continue  # 같은 저장소의 액션과 재사용 워크플로, 컨테이너 이미지는 이 검사의 대상이 아니다
            where = f"{path.relative_to(ROOT).as_posix()}:{number}"
            target, _, version = ref.partition("@")
            if not SHA.match(version):
                problems.append(("P1", where, f"{target}@{version or '(판 없음)'}: 커밋 SHA로 고정하지 않았다"))
            elif not (found.group(2) and VERSION_COMMENT.search(found.group(2))):
                problems.append(("P1", where, f"{target}: SHA 뒤에 # vX.Y.Z 주석이 없다"))


def check_lock(problems):
    lock = ROOT / "requirements.lock"
    if not lock.is_file():
        problems.append(("P2", "requirements.lock", "잠금 파일이 없다"))
        return
    lines = lock.read_text(encoding="utf-8").splitlines()
    locked = {}
    for index, line in enumerate(lines):
        found = LOCK_LINE.match(line)
        if found:
            locked[normalize(found.group(1))] = found.group(2)
            following = lines[index + 1] if index + 1 < len(lines) else ""
            if "--hash=sha256:" not in following:
                problems.append(("P2", f"requirements.lock:{index + 1}", f"{found.group(1)}에 해시가 없다"))
        elif line and not line[0].isspace() and not line.startswith("#"):
            problems.append(("P2", f"requirements.lock:{index + 1}", f"==로 고정되지 않은 줄: {line[:40]}"))
    req = ROOT / "requirements.txt"
    if req.is_file():
        for line in req.read_text(encoding="utf-8").splitlines():
            found = REQ_PIN.match(line.strip())
            if found:
                name, version = normalize(found.group(1)), found.group(2)
                if locked.get(name) != version:
                    problems.append(("P2", "requirements.lock",
                                     f"{name}=={version}이 잠금 파일에 없다(잠금: {locked.get(name)}). pip-compile을 다시 한다"))


def check_python(problems):
    pin = ROOT / ".python-version"
    if not pin.is_file() or not pin.read_text(encoding="utf-8").strip():
        problems.append(("P3", ".python-version", "파이썬 판을 적은 파일이 없다"))
    texts = [p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.y*ml")] if WORKFLOWS.is_dir() else []
    for text in texts:
        if "setup-python" in text and "python-version-file: .python-version" not in text:
            problems.append(("P3", ".github/workflows/", "setup-python이 .python-version을 읽지 않는다"))
            break


def check_env_example(problems):
    path = ROOT / ".env.example"
    values = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    model = values.get("LLM_MODEL", "")
    if not model:
        problems.append(("P4", ".env.example", "LLM_MODEL이 비어 있다"))
    elif model.endswith("-latest"):
        problems.append(("P4", ".env.example", f"LLM_MODEL={model}: 별칭은 가리키는 모델이 바뀔 수 있다"))
    for key in ("PROMPT_SUMMARY", "PROMPT_ASK"):
        if not values.get(key):
            problems.append(("P5", ".env.example", f"{key}가 비어 있다"))


def main():
    problems = []
    check_actions(problems)
    check_lock(problems)
    check_python(problems)
    check_env_example(problems)
    for code, where, detail in problems:
        print(f"{code}  {where}  {detail}")
    print(f"고정 검사: 문제 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
