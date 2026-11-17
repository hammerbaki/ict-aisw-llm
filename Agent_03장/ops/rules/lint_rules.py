"""팀 규칙 파일 자체를 검사한다. 규칙 파일도 코드처럼 리뷰와 검사의 대상이다.

검사 항목
  C1  CLAUDE.md: 200줄 이하, '실행 명령'·'작업 규칙'·'금지' 절, 금지 항목마다 '이유:'
  C2  .claude/rules/*.md: 머리말의 paths가 있고, 패턴마다 실제 파일이 하나 이상 맞는다
  C3  .claude/settings.json: JSON 문법, permissions의 키, 규칙의 모양, .env 읽기 거부
  C4  개인 설정(.claude/settings.local.json, CLAUDE.local.md)이 git에 올라가지 않는다
  C5  PR 템플릿과 저장소 규약 문서가 있다
  C6  CODEOWNERS: 줄의 모양, 규칙 파일에 소유자가 있다

쓰는 법 (저장소 폴더에서)
    python ops/rules/lint_rules.py            지금 폴더의 저장소를 검사
    python ops/rules/lint_rules.py --repo 경로
실패가 하나라도 있으면 종료 코드 1이다. '주의'는 실패로 세지 않는다.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from globmatch import matches  # noqa: E402
from perm_sim import judge, load_settings  # noqa: E402

MAX_CLAUDE_MD = 200  # 공식 문서의 권장: 파일 하나에 200줄 미만
REQUIRED_SECTIONS = ("실행 명령", "작업 규칙", "금지")
# code.claude.com/docs/en/settings-reference 에서 확인한 permissions 아래의 키(2026-11-14)
PERMISSION_KEYS = {"allow", "ask", "deny", "additionalDirectories", "defaultMode",
                   "disableBypassPermissionsMode", "disableAutoMode", "denyInsteadOfPrompting",
                   "blockReadsOutsideWorkingDirectories", "blockWritesOutsideWorkingDirectories"}
KNOWN_TOOLS = {"Bash", "PowerShell", "Read", "Edit", "Write", "NotebookEdit", "Glob", "Grep",
               "WebFetch", "WebSearch", "Agent", "Skill"}
RULE = re.compile(r"^(?P<tool>[A-Za-z_*][\w*]*)(?:\((?P<arg>.+)\))?$", re.S)


class Report:
    def __init__(self):
        self.failed = 0
        self.warned = 0

    def ok(self, cid, text):
        print(f"통과 {cid} {text}")

    def fail(self, cid, text):
        self.failed += 1
        print(f"실패 {cid} {text}")

    def warn(self, cid, text):
        self.warned += 1
        print(f"주의 {cid} {text}")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
                          capture_output=True, text=True, encoding="utf-8")


def repo_files(repo):
    """저장소의 파일 목록(추적 중인 것과, 무시되지 않은 새 파일)."""
    tracked = git(repo, "ls-files")
    if tracked.returncode == 0:
        others = git(repo, "ls-files", "--others", "--exclude-standard").stdout
        return [p for p in (tracked.stdout + others).splitlines() if p]
    files = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", ".venv", "venv", "__pycache__")]
        for name in names:
            files.append(os.path.relpath(os.path.join(root, name), repo).replace("\\", "/"))
    return files


def placeholder(report, cid, name, text):
    """양식의 자리 표시 「」가 남아 있으면 실패로 센다."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # 양식의 안내 주석은 세지 않는다
    left = [line.strip() for line in text.splitlines() if "「" in line]
    if left:
        report.fail(cid, f"{name}: 채우지 않은 자리 표시 「」가 {len(left)}줄 남아 있다. 예: {left[0][:40]}")


def sections(text):
    """'## 제목' 단위로 {제목: [줄, ...]}를 돌려준다."""
    result, current = {}, None
    for line in text.splitlines():
        found = re.match(r"^#{1,3}\s+(.*)$", line)
        if found:
            current = found.group(1).strip()
            result[current] = []
        elif current is not None:
            result[current].append(line)
    return result


def check_claude_md(repo, report):
    path = repo / "CLAUDE.md"
    if not path.exists():
        path = repo / ".claude" / "CLAUDE.md"
    if not path.exists():
        report.fail("C1", "CLAUDE.md가 없다(저장소 루트 또는 .claude/)")
        return
    text = path.read_text(encoding="utf-8")
    placeholder(report, "C1", "CLAUDE.md", text)
    lines = text.splitlines()
    if len(lines) > MAX_CLAUDE_MD:
        report.fail("C1", f"CLAUDE.md가 {len(lines)}줄이다({MAX_CLAUDE_MD}줄 이하로 줄인다)")
    else:
        report.ok("C1", f"CLAUDE.md {len(lines)}줄")
    found = sections(text)
    for name in REQUIRED_SECTIONS:
        title = next((t for t in found if name in t), None)
        if title is None:
            report.fail("C1", f"'{name}' 절이 없다")
            continue
        bullets = [l for l in found[title] if l.lstrip().startswith("- ")]
        if not bullets:
            report.fail("C1", f"'{title}' 절에 항목이 없다")
        elif name == "금지":
            missing = [b.strip() for b in bullets if "이유:" not in b]
            if missing:
                report.fail("C1", f"금지 항목 {len(missing)}개에 '이유:'가 없다. 예: {missing[0][:40]}")
            else:
                report.ok("C1", f"금지 항목 {len(bullets)}개 모두 이유가 있다")
    if "pytest" not in text:
        report.warn("C1", "실행 명령에 테스트 명령(pytest)이 보이지 않는다")


YAML_SPECIAL = tuple("*&!@`{[|>%")  # YAML에서 따옴표 없이 값의 첫 글자로 쓰면 다른 뜻이 되는 글자


def unquoted_special(text):
    """머리말에서 따옴표 없이 YAML 특수 문자로 시작하는 paths 값(예: **/*.py)을 찾는다.

    YAML은 따옴표 없는 *로 시작하는 값을 별칭(alias)으로 읽다가 오류를 낸다. 그러면 Claude Code는
    머리말을 무시하고 그 규칙을 paths가 없는 것처럼, 곧 매 세션 읽는다.
    """
    found = []
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        item = re.match(r"^\s+-\s+(.*)$", line) or re.match(r"^paths\s*:\s*(.+)$", line)
        if item and item.group(1).strip().startswith(YAML_SPECIAL):
            found.append(item.group(1).strip())
    return found


def read_paths(text):
    """규칙 파일 머리말의 paths를 읽는다. 머리말이 없으면 None이다."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    paths, in_paths = [], False
    for line in lines[1:end]:
        if re.match(r"^paths\s*:", line):
            rest = line.split(":", 1)[1].strip()
            if rest:
                paths.extend(p.strip().strip("\"'") for p in rest.split(",") if p.strip())
            in_paths = True
        elif in_paths and re.match(r"^\s+-\s+", line):
            paths.append(line.split("-", 1)[1].strip().strip("\"'"))
        else:
            in_paths = False
    return paths


def check_rules(repo, report, files):
    folder = repo / ".claude" / "rules"
    rules = sorted(folder.rglob("*.md")) if folder.exists() else []
    if not rules:
        report.fail("C2", ".claude/rules/에 규칙 파일이 없다")
        return
    for rule in rules:
        name = rule.relative_to(repo).as_posix()
        text = rule.read_text(encoding="utf-8")
        placeholder(report, "C2", name, text)
        for value in unquoted_special(text):
            report.fail("C2", f"{name}: '{value}'를 따옴표로 감싼다. YAML 오류로 머리말 전체가 무시된다")
        paths = read_paths(text)
        if paths is None:
            report.warn("C2", f"{name}: 머리말(paths)이 없어 매 세션 읽힌다")
            continue
        if not paths:
            report.fail("C2", f"{name}: 머리말에 paths 항목이 없다")
            continue
        for pattern in paths:
            hits = [f for f in files if matches(pattern, f)]
            if hits:
                report.ok("C2", f"{name}: '{pattern}'에 맞는 파일 {len(hits)}개")
            else:
                report.fail("C2", f"{name}: '{pattern}'에 맞는 파일이 없다(패턴을 확인한다)")


def check_settings(repo, report):
    path = repo / ".claude" / "settings.json"
    if not path.exists():
        report.fail("C3", ".claude/settings.json이 없다")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        report.fail("C3", f"settings.json의 JSON 문법 오류: {error.msg} ({error.lineno}행 {error.colno}열)")
        return
    report.ok("C3", "settings.json의 JSON 문법")
    perms = data.get("permissions")
    if not isinstance(perms, dict):
        report.fail("C3", "permissions 객체가 없다")
        return
    for key in perms:
        if key not in PERMISSION_KEYS:
            report.warn("C3", f"permissions.{key}: 문서에서 확인한 키가 아니다(철자를 확인한다)")
    if perms.get("defaultMode") in ("auto", "bypassPermissions"):
        report.fail("C3", f"defaultMode '{perms['defaultMode']}'는 프로젝트 설정에서 효과가 없다")
    count = 0
    for kind in ("allow", "ask", "deny"):
        for rule in perms.get(kind, []):
            count += 1
            found = RULE.match(rule)
            if not found:
                report.fail("C3", f"{kind}: 규칙의 모양이 'Tool' 또는 'Tool(지정자)'가 아니다: {rule}")
                continue
            tool, arg = found["tool"], found["arg"]
            if tool not in KNOWN_TOOLS and not tool.startswith("mcp__") and "*" not in tool:
                report.warn("C3", f"{kind}: '{tool}'은(는) 알려진 도구 이름이 아니다: {rule}")
            if tool in ("Write", "Glob", "Grep") and arg not in (None, "*"):
                report.warn("C3", f"{kind}: {tool}(경로) 규칙은 맞추어지지 않는다. Edit 또는 Read로 쓴다: {rule}")
            if kind == "allow" and tool == "Bash" and arg and "*" in arg.rstrip("*").rstrip():
                report.warn("C3", f"allow: 별표 뒤에 글자가 이어진다. 의도보다 넓게 맞을 수 있다: {rule}")
    report.ok("C3", f"권한 규칙 {count}개의 모양")
    kind, _ = judge(load_settings([path]), "Read(.env)")
    if kind == "deny":
        report.ok("C3", ".env 읽기가 거부된다")
    else:
        report.fail("C3", ".env 읽기를 거부하는 규칙이 없다(Read(./.env))")


def check_personal(repo, report):
    for name in (".claude/settings.local.json", "CLAUDE.local.md"):
        tracked = git(repo, "ls-files", "--error-unmatch", name).returncode == 0
        # -v는 무시 규칙이 나온 파일을 알려 준다. 저장소의 .gitignore가 아니라 이 컴퓨터의
        # 전역 제외 파일(core.excludesFile 등)에만 있으면 다른 팀원의 컴퓨터에서는 무시되지 않는다.
        found = git(repo, "check-ignore", "-v", "--no-index", name)
        parsed = re.match(r"^(.*):(\d+):(.*)\t", found.stdout) if found.returncode == 0 else None
        source = parsed.group(1) if parsed else ""
        if tracked:
            report.fail("C4", f"{name}이(가) 저장소에 올라가 있다(git rm --cached로 내린다)")
        elif not source:
            report.fail("C4", f"{name}이(가) .gitignore에 없다")
        elif not source.replace("\\", "/").endswith(".gitignore"):
            report.fail("C4", f"{name}은(는) 이 컴퓨터의 전역 제외 파일({source})에서만 무시된다. "
                              "저장소의 .gitignore에도 적는다")
        else:
            report.ok("C4", f"{name}은(는) {source}에 의해 무시된다")


def check_templates(repo, report):
    candidates = [".github/pull_request_template.md", "pull_request_template.md", "docs/pull_request_template.md"]
    found = next((c for c in candidates if (repo / c).exists()), None)
    if found is None:
        report.fail("C5", "PR 템플릿(.github/pull_request_template.md)이 없다")
    else:
        text = (repo / found).read_text(encoding="utf-8")
        placeholder(report, "C5", found, text)
        if "- [ ]" in text:
            report.ok("C5", f"PR 템플릿 {found}")
        else:
            report.warn("C5", f"{found}에 점검 항목(- [ ])이 없다")
    convention = repo / "docs" / "운영" / "저장소규약.md"
    if convention.exists():
        placeholder(report, "C5", "docs/운영/저장소규약.md", convention.read_text(encoding="utf-8"))
        report.ok("C5", "docs/운영/저장소규약.md")
    else:
        report.fail("C5", "docs/운영/저장소규약.md가 없다")


def owners_of(lines, path):
    """CODEOWNERS에서 path에 맞는 마지막 줄의 소유자 목록. 없으면 None이다."""
    owners = None
    for pattern, names in lines:
        pat = pattern + "**" if pattern.endswith("/") else pattern
        if matches(pat, path):
            owners = names
    return owners


def check_codeowners(repo, report):
    found = next((repo / c for c in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
                  if (repo / c).exists()), None)
    if found is None:
        report.fail("C6", "CODEOWNERS가 없다(.github/, 루트, docs/ 중 한 곳)")
        return
    lines = []
    placeholder(report, "C6", "CODEOWNERS", found.read_text(encoding="utf-8"))
    for number, raw in enumerate(found.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        pattern, *names = line.split()
        if pattern.startswith("!") or "[" in pattern:
            report.fail("C6", f"{number}행: CODEOWNERS는 '!'와 '[ ]'를 지원하지 않는다: {line}")
        bad = [n for n in names if "@" not in n]
        if bad:
            report.fail("C6", f"{number}행: 소유자는 @아이디, @조직/팀, 이메일이어야 한다: {bad[0]}")
        if any(not n.isascii() for n in names):
            report.warn("C6", f"{number}행: 소유자에 자리 표시(한글)가 남아 있다: {' '.join(names)}")
        lines.append((pattern, names))
    report.ok("C6", f"{found.relative_to(repo).as_posix()} 규칙 {len(lines)}줄")
    for target in ("CLAUDE.md", ".claude/settings.json", "CODEOWNERS"):
        owners = owners_of(lines, target)
        if owners:
            report.ok("C6", f"{target}의 소유자: {' '.join(owners)}")
        else:
            report.fail("C6", f"{target}에 소유자가 없다(규칙 파일도 리뷰 대상이다)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="팀 규칙 파일 검사")
    parser.add_argument("--repo", default=".", help="저장소 폴더(기본: 지금 폴더)")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    report = Report()
    files = repo_files(repo)
    check_claude_md(repo, report)
    check_rules(repo, report, files)
    check_settings(repo, report)
    check_personal(repo, report)
    check_templates(repo, report)
    check_codeowners(repo, report)
    print(f"실패 {report.failed}건, 주의 {report.warned}건")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
