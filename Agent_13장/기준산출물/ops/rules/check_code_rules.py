"""저장소의 코드가 팀 규칙(CLAUDE.md, .claude/rules/)을 지키는지 기계로 검사한다 (3장 기준산출물의 간단한 견본).

3장의 ops/rules/lint_rules.py가 규칙 파일 자체를 검사한다면, 이 견본은 규칙이 코드에서 지켜지는지를 본다.
CI가 풀 리퀘스트마다 부르므로 표준 라이브러리만 쓴다. 기계로 셀 수 있는 규칙만 검사한다.

규칙
  llm-bypass         모든 LLM 호출은 api/llm.py를 거친다: 다른 .py 파일에서 anthropic을 불러오지 않는다
  inner-html         웹은 textContent로만 글을 넣는다: web/에 innerHTML, outerHTML, insertAdjacentHTML이 없다
  model-name         모델 이름은 코드에 적지 않고 LLM_MODEL로 받는다: api/, rag/, web/에 claude-로 시작하는 모델 이름이 없다
  prompt-file        기본 프롬프트 판본과 .env.example의 PROMPT_* 값이 prompts/에 파일로 있다
  personal-settings  개인 설정(.claude/settings.local.json, CLAUDE.local.md)이 git에 올라가 있지 않다

쓰는 법 (저장소 폴더에서)
    python ops/rules/check_code_rules.py
위반이 하나라도 있으면 종료 코드 1이다.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

ANTHROPIC_IMPORT = re.compile(r"^\s*(?:import\s+anthropic\b|from\s+anthropic\b)")
INNER_HTML = re.compile(r"\b(?:innerHTML|outerHTML|insertAdjacentHTML)\b")
MODEL_NAME = re.compile(r"""["'`]claude-[a-z0-9.-]+["'`]""")
PROMPT_ENV = re.compile(r"^\s*(PROMPT_[A-Z]+)\s*=\s*(\S+)")
DEFAULT_PROMPTS = ("summary_v1", "ask_v1")  # api/llm.py의 prompt_version() 기본값
PERSONAL = (".claude/settings.local.json", "CLAUDE.local.md")


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def read(path):
    try:
        return (ROOT / path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def check(files):
    problems = []
    for path in files:
        if path.endswith(".py") and path != "api/llm.py" and not path.startswith("tests/"):
            for number, line in enumerate(read(path), 1):
                if ANTHROPIC_IMPORT.search(line):
                    problems.append(("llm-bypass", f"{path}:{number}", line.strip()))
        if path.startswith("web/") and path.endswith((".js", ".html")):
            for number, line in enumerate(read(path), 1):
                if INNER_HTML.search(line):
                    problems.append(("inner-html", f"{path}:{number}", line.strip()))
        if path.startswith(("api/", "rag/", "web/")):
            for number, line in enumerate(read(path), 1):
                if MODEL_NAME.search(line):
                    problems.append(("model-name", f"{path}:{number}", line.strip()))
        if path in PERSONAL:
            problems.append(("personal-settings", path, "개인 설정이 저장소에 있다"))

    wanted = {name: "api/llm.py 기본값" for name in DEFAULT_PROMPTS}
    for line in read(".env.example"):
        found = PROMPT_ENV.match(line)
        if found:
            wanted[found.group(2)] = f".env.example의 {found.group(1)}"
    for name, origin in sorted(wanted.items()):
        if not (ROOT / "prompts" / f"{name}.txt").is_file():
            problems.append(("prompt-file", f"prompts/{name}.txt", f"{origin}가 가리키는 파일이 없다"))
    return problems


def main():
    try:
        files = tracked()
    except (OSError, subprocess.CalledProcessError):
        print("git 저장소에서 실행한다")
        return 2
    problems = check(files)
    for rule, where, detail in problems:
        print(f"위반  {rule:<17} {where}  {detail[:80]}")
    print(f"검사한 파일 {len(files)}개, 위반 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
