"""가짜 구현 에이전트: 작업 카드에 맞는 정답 변경을 작업 공간에 적용하고, 결과 보고를 쓰고, 커밋한다.

dispatch.sh가 「claude -p」 자리에 이 스크립트를 넣어 부른다. 인터페이스는 같다.
작업 공간(worktree) 안에서 실행되고, 마지막 인자로 지시문을 받는다. 지시문에서 카드 경로와 시도 번호를 읽는다.

사용법 (dispatch.sh가 부른다)
    AGENT_CMD="python ops/multi/fake/impl_agent.py" bash ops/multi/dispatch.sh ISSUE-07 T1 T2

시나리오 (환경 변수 FAKE_SCENARIO, 작업마다 「작업=시나리오」를 쉼표로. 기본은 모두 ok)
    ok         정답 변경을 적용한다
    fail_once  첫 시도에 틀린 변경(T1: 중복 번호를 없애지 않음, T2: innerHTML 사용)을 내고, 둘째 시도부터 고친다
    scope      정답에 더해 소유 밖 파일(docs/요구사항명세서.md)도 고친다. 매 시도 범위 검사에서 거부된다
    crash      아무것도 하지 않고 종료 코드 1로 끝난다
    crash가 아니면 공유 파일 docs/운영/변경기록.md의 맨 끝에 그 작업의 줄 하나를 더한다(두 작업이 같은 자리에 더하므로
    뒤에 병합하는 작업에서 충돌한다. 10장 핵심 실습의 충돌).
    예) FAKE_SCENARIO="T1=ok,T2=fail_once"
환경 변수 FAKE_DELAY(초, 기본 1)만큼 기다린 뒤 일한다. 병렬 실행이 겹치는 것을 보이기 위해서다.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.cwd()                                     # 작업 공간의 맨 위
ANSWERS = Path(__file__).resolve().parent / "answers"
SPEC = "docs/요구사항명세서.md"
CHANGELOG = "docs/운영/변경기록.md"   # 카드의 「- 공유 파일:」. 작업마다 맨 끝에 자기 줄 하나를 더한다
CHANGELOG_LINES = {
    "T1": "- ISSUE-07 T1: 관심 공고 내보내기 API GET /api/favorites/export (REQ-FAV-03, 04)",
    "T2": "- ISSUE-07 T2: 목록 화면의 관심 공고 내보내기 단추 (REQ-FAV-05)",
}


def run_git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout


def insert_after(path, anchor, new_text):
    """anchor로 시작하는 첫 줄 다음에 new_text를 넣는다. 이미 들어 있으면 그대로 둔다."""
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    if new_text.strip() in text:
        return
    lines = text.split("\n")
    at = next((i for i, line in enumerate(lines) if line.strip().startswith(anchor)), None)
    if at is None:
        raise SystemExit(f"{path}에서 「{anchor}」 줄을 찾지 못하였다. 사람에게 넘긴다")
    lines[at + 1:at + 1] = new_text.split("\n")
    file.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def append_changelog(task):
    """공유 파일인 변경 기록의 맨 끝에 이 작업의 줄 하나를 더한다. 이미 있으면 그대로 둔다."""
    file = ROOT / CHANGELOG
    if not file.exists():
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("# 운영 변경 기록\n\n", encoding="utf-8", newline="\n")
    text = file.read_text(encoding="utf-8")
    line = CHANGELOG_LINES[task]
    if line in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    file.write_text(text + line + "\n", encoding="utf-8", newline="\n")


def apply_t1(broken):
    shutil.copyfile(ANSWERS / "T1" / "api" / "export.py", ROOT / "api" / "export.py")
    if broken:   # 첫 시도의 실수: 같은 번호를 한 번만 넣는 계약을 빠뜨렸다
        file = ROOT / "api" / "export.py"
        file.write_text(file.read_text(encoding="utf-8").replace(
            "        if int(part) not in ids:\n            ids.append(int(part))",
            "        ids.append(int(part))"), encoding="utf-8", newline="\n")
    insert_after("api/main.py", "from fastapi.middleware.cors import", "from fastapi.responses import Response")
    insert_after("api/main.py", "from api.summary import", "from api import export  # noqa: E402")
    main = ROOT / "api" / "main.py"
    endpoint = (ANSWERS / "T1" / "main_endpoint.txt").read_text(encoding="utf-8")
    text = main.read_text(encoding="utf-8")
    if '"/api/favorites/export"' not in text:
        main.write_text(text.rstrip("\n") + "\n" + endpoint, encoding="utf-8", newline="\n")
    return ["api/export.py", "api/main.py"]


def apply_t2(broken):
    shutil.copyfile(ANSWERS / "T2" / "web" / "js" / "export.js", ROOT / "web" / "js" / "export.js")
    if broken:   # 첫 시도의 실수: 상태 줄에 innerHTML로 글을 넣었다
        file = ROOT / "web" / "js" / "export.js"
        file.write_text(file.read_text(encoding="utf-8").replace(
            "  showStatus(statusBox, `관심 공고 ${ids.length}건을 내보냈다.`);",
            "  statusBox.innerHTML = `<b>관심 공고 ${ids.length}건</b>을 내보냈다.`;"), encoding="utf-8", newline="\n")
    insert_after("web/index.html", "</form>",
                 '    <p class="actions"><button id="export-favorites" type="button">관심 공고 내보내기(CSV)</button></p>')
    insert_after("web/index.html", '<script src="js/list.js">', '  <script src="js/export.js"></script>')
    return ["web/js/export.js", "web/index.html"]


TASKS = {
    "T1": (apply_t1, "feat(api): 관심 공고 내보내기 API(REQ-FAV-03, 04)", "pytest -q --ignore=tests/test_web_export.py"),
    "T2": (apply_t2, "feat(web): 관심 공고 내보내기 단추(REQ-FAV-05)", "pytest -q --ignore=tests/test_favorites_export.py"),
}


def scenario_for(task):
    for item in os.environ.get("FAKE_SCENARIO", "").split(","):
        if "=" in item:
            name, value = item.split("=", 1)
            if name.strip() == task:
                return value.strip()
    return "ok"


def write_report(issue, task, attempt, files, test_line, scenario):
    request = "없음"
    if scenario == "scope":
        request = "없음 (명세서의 상태도 직접 고쳤다)"
    else:
        request = f"명세서의 {'REQ-FAV-03, 04' if task == 'T1' else 'REQ-FAV-05'} 상태를 병합 뒤에 고쳐야 한다"
    risk = "없음" if task == "T1" else "단추를 눌러 파일이 내려받아지는지는 브라우저에서 확인하지 못하였다"
    rows = "\n".join(f"| `{path}` | {'새 파일' if path.endswith(('export.py', 'export.js')) else ('끝에 한 줄' if path == CHANGELOG else '고침')} |" for path in files)
    text = f"""# 결과 보고 {issue} {task}

- 작업: {issue} {task}, 시도 {attempt}
- 맡은 역할: implementer (가짜 에이전트 ops/multi/fake/impl_agent.py)
- 결과: 완료

## 바꾼 파일

| 파일 | 무엇을 |
|---|---|
{rows}

## 확인

```text
{TASKS[task][2]} → {test_line}
```

## 계약과 다른 점

없음

## 요청 (소유 파일 밖에서 필요한 일)

{request}

## 남은 위험

{risk}
"""
    path = f"docs/운영/인계/{issue}/{task}_보고.md"
    (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")
    return path


def main():
    prompt = sys.argv[-1] if len(sys.argv) > 1 else ""
    card = re.search(r"docs/운영/인계/(ISSUE-\d+)/(T\d+)_카드\.md", prompt)
    attempt = re.search(r"시도 (\d+)/", prompt)
    if not card:
        print("지시문에서 작업 카드 경로를 찾지 못하였다")
        return 2
    issue, task = card.group(1), card.group(2)
    attempt = int(attempt.group(1)) if attempt else 1
    if task not in TASKS:
        print(f"이 가짜 에이전트는 {task}의 정답을 모른다")
        return 2
    scenario = scenario_for(task)
    time.sleep(float(os.environ.get("FAKE_DELAY", "1")))
    print(f"[가짜 implementer] {issue} {task} 시도 {attempt}, 시나리오 {scenario}, 작업 공간 {ROOT}")
    if scenario == "crash":
        print("[가짜 implementer] 중간에 멈춤(종료 코드 1)")
        return 1

    apply, message, test_cmd = TASKS[task]
    broken = scenario == "fail_once" and attempt == 1
    files = apply(broken)
    append_changelog(task)
    files.append(CHANGELOG)
    if scenario == "scope":
        spec = ROOT / SPEC
        spec.write_text(spec.read_text(encoding="utf-8").replace(
            "| **미구현** | `test_favorites_export.py` |" if task == "T1" else "| **미구현** | `test_web_export.py`(정적 검사) |",
            "| 구현 | `test_favorites_export.py` |" if task == "T1" else "| 구현(수동) | `test_web_export.py`(정적 검사) |"),
            encoding="utf-8", newline="\n")
        files.append(SPEC)

    result = subprocess.run([sys.executable, "-m", *test_cmd.split()], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    test_line = lines[-1] if lines else "(출력 없음)"
    print(f"[가짜 implementer] {test_cmd} → {test_line}")

    report = write_report(issue, task, attempt, files, test_line, scenario)
    run_git("add", *files, report)
    body = f"{message}\n\nAgent-Role: implementer\nAgent-Task: {issue}/{task}\nAgent-Attempt: {attempt}\n"
    run_git("commit", "-q", "-m", body)
    print(f"[가짜 implementer] 커밋 {run_git('rev-parse', '--short', 'HEAD').strip()}: {message}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
