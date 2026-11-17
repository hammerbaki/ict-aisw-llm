"""변경 내역(diff)에서 팀 규칙의 위반을 세어 표로 낸다. 규칙이 있을 때와 없을 때의 결과를 비교하는 데 쓴다.

검사하는 것은 CLAUDE.md와 .claude/rules/의 규칙 가운데 기계로 셀 수 있는 것뿐이다.
규칙의 문장이 바뀌면 아래 CHECKS도 함께 고친다. 위반 0건이 규칙을 모두 지켰다는 뜻은 아니다.

쓰는 법 (저장소 폴더에서)
    python ops/rules/count_violations.py --base tdd-1                 tdd-1부터 HEAD까지의 커밋
    python ops/rules/count_violations.py --repo ../compare/no-rules --base tdd-1
    python ops/rules/count_violations.py --diff 견본/비교/규칙없음.diff  저장해 둔 diff 파일
    --markdown 을 붙이면 규칙비교.md에 붙일 표를 낸다.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_commits import check_message, commits_in_range  # noqa: E402

PROTECTED_DIRS = ("data/",)  # 고치면 안 되는 폴더
PROTECTED_FILES = ("tests/.baseline.json", ".env")  # 고치면 안 되는 파일(.env.example은 제외)
FEATURE_DIRS = ("api/", "rag/", "web/")  # 기능 코드가 있는 폴더


def parse_diff(text):
    """unified diff를 읽어 {경로: [더한 줄, ...]}를 돌려준다. 지운 파일은 빈 목록으로 둔다."""
    files = {}
    current = None
    for line in text.split("\n"):
        if line.startswith("diff --git "):
            found = re.match(r'diff --git "?a/(.+?)"? "?b/(.+?)"?$', line)
            current = found.group(2) if found else None
            if current is not None:
                files.setdefault(current, [])
        elif line.startswith("+++ ") or line.startswith("--- "):
            continue
        elif current is not None and line.startswith("+"):
            files[current].append(line[1:])
    return files


def added(files, prefix=None, suffix=None, exclude=()):
    """조건에 맞는 파일의 (경로, 줄) 쌍을 차례로 내준다."""
    for path, lines in files.items():
        if prefix and not path.startswith(prefix):
            continue
        if suffix and not path.endswith(suffix):
            continue
        if path in exclude:
            continue
        for line in lines:
            yield path, line


def find(files, pattern, **where):
    regex = re.compile(pattern)
    return [f"{path}: {line.strip()[:60]}" for path, line in added(files, **where) if regex.search(line)]


def check_llm_direct(files):
    """LLM 호출은 api/llm.py만 거친다: 다른 파일에서 anthropic을 직접 쓰면 위반."""
    return find(files, r"^\s*(import anthropic|from anthropic)|anthropic\.Anthropic\(",
                suffix=".py", exclude=("api/llm.py",))


def check_model_literal(files):
    """모델 이름은 환경 변수 LLM_MODEL로만 받는다: 코드에 모델 이름을 적으면 위반."""
    return find(files, r"claude-(haiku|sonnet|opus)", suffix=".py")


def check_print(files):
    """기록은 logging으로 남긴다: api/와 rag/에서 print를 쓰면 위반."""
    return (find(files, r"(^|[^\w.])print\(", prefix="api/", suffix=".py")
            + find(files, r"(^|[^\w.])print\(", prefix="rag/", suffix=".py"))


def check_inner_html(files):
    """웹 화면에 글은 textContent로만 넣는다: innerHTML 등을 쓰면 위반."""
    return find(files, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", prefix="web/")


def check_protected(files):
    """data/, tests/.baseline.json, .env를 고치면 위반."""
    def protected(path):
        if path.startswith(PROTECTED_DIRS) or path in PROTECTED_FILES:
            return True
        return path.startswith(".env.") and path != ".env.example"
    return [path for path in files if protected(path)]


def check_secret(files):
    """키처럼 보이는 값을 더하면 위반(.env.example의 빈 값은 제외)."""
    return find(files, r"sk-ant-[A-Za-z0-9_-]{8,}|ANTHROPIC_API_KEY\s*=\s*\S+")


def check_tests_missing(files):
    """api/나 rag/의 코드를 바꾸었는데 tests/가 그대로이면 위반 1건."""
    code = [p for p in files if p.startswith(("api/", "rag/")) and p.endswith(".py")]
    tests = [p for p in files if p.startswith("tests/") and p.endswith(".py")]
    return [f"코드 {len(code)}개 파일이 바뀌었으나 테스트 변경 없음"] if code and not tests else []


def check_spec_missing(files):
    """기능 폴더를 바꾸었는데 요구사항명세서가 그대로이면 위반 1건."""
    feature = [p for p in files if p.startswith(FEATURE_DIRS)]
    spec = "docs/요구사항명세서.md" in files
    return [f"기능 {len(feature)}개 파일이 바뀌었으나 명세서 변경 없음"] if feature and not spec else []


MODULE_MARK = re.compile(r"^pytestmark\s*=.*REQ-", re.M)


def check_test_req_id(files, read_file=None):
    """새 테스트에 요구 마커(2장의 pytest.mark.req)가 없으면 위반.

    함수 바로 위의 @pytest.mark.req(id="REQ-…")나 파일 맨 위의 pytestmark = pytest.mark.req(…)를 찾는다.
    read_file이 있으면(--base 모드) 변경 뒤 파일 전체에서 pytestmark를 찾는다.
    """
    problems = []
    for path, lines in files.items():
        if not (path.startswith("tests/") and path.endswith(".py")):
            continue
        module_marked = bool(MODULE_MARK.search("\n".join(lines)))
        if not module_marked and read_file is not None:
            module_marked = bool(MODULE_MARK.search(read_file(path)))
        for i, line in enumerate(lines):
            if re.match(r"\s*def test_", line) and not module_marked:
                window, j = [], i - 1
                while j >= 0 and lines[j].strip().startswith(("@", "#")):  # 바로 위의 데코레이터와 주석
                    window.append(lines[j])
                    j -= 1
                if not any("REQ-" in near for near in window):
                    problems.append(f"{path}: {line.strip()[:60]}")
    return problems


CHECKS = [
    ("R1", "LLM 호출은 api/llm.py만 거친다", check_llm_direct),
    ("R2", "모델 이름을 코드에 적지 않는다", check_model_literal),
    ("R3", "api/·rag/에서 print 대신 logging", check_print),
    ("R4", "web/에서 innerHTML 쓰지 않음", check_inner_html),
    ("R5", "보호 경로(data/, 동결 기록, .env) 수정 금지", check_protected),
    ("R6", "키 값을 코드와 문서에 넣지 않음", check_secret),
    ("R7", "코드를 바꾸면 테스트도 바꾼다", check_tests_missing),
    ("R8", "기능을 바꾸면 명세서도 고친다", check_spec_missing),
    ("R9", "새 테스트에 요구 마커(REQ-ID)", check_test_req_id),
]


def count(files, commits=None, read_file=None):
    """[(ID, 설명, 위반 목록)]을 돌려준다. commits가 있으면 커밋 메시지 검사(R10)를 더한다."""
    rows = [(rid, desc, func(files, read_file) if func is check_test_req_id else func(files))
            for rid, desc, func in CHECKS]
    if commits is not None:
        bad = [f"{sha}: {msg.strip().splitlines()[0] if msg.strip() else ''}"
               for sha, msg in commits if check_message(msg)]
        rows.append(("R10", "커밋 메시지가 규약을 따른다", bad))
    return rows


def print_table(rows, markdown=False, label=""):
    total = sum(len(found) for _, _, found in rows)
    if markdown:
        print(f"| 규칙 | 내용 | 위반 수{(' (' + label + ')') if label else ''} | 예 |")
        print("|---|---|---|---|")
        for rid, desc, found in rows:
            example = found[0].replace("|", "\\|") if found else ""
            print(f"| {rid} | {desc} | {len(found)} | {example} |")
        print(f"| 합계 | | {total} | |")
    else:
        for rid, desc, found in rows:
            print(f"{rid:4} {len(found):3}  {desc}")
            for item in found[:3]:
                print(f"           - {item}")
        print(f"합계 {total}")
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description="변경 내역의 규칙 위반 세기")
    parser.add_argument("--repo", default=".", help="저장소 폴더(기본: 지금 폴더)")
    parser.add_argument("--base", help="비교의 시작점(태그, 브랜치, 커밋). HEAD까지의 커밋을 본다")
    parser.add_argument("--head", default="HEAD", help="비교의 끝(기본: HEAD)")
    parser.add_argument("--diff", help="저장해 둔 diff 파일(이때 커밋 메시지는 검사하지 않는다)")
    parser.add_argument("--markdown", action="store_true", help="마크다운 표로 낸다")
    parser.add_argument("--label", default="", help="표 머리에 붙일 조건 이름(예: 규칙 없음)")
    args = parser.parse_args(argv)

    read_file = None
    if args.diff:
        text = Path(args.diff).read_text(encoding="utf-8")
        commits = None
    elif args.base:
        # core.quotePath=false: 한글 파일 이름을 8진수 escape로 바꾸지 않고 그대로 낸다
        result = subprocess.run(["git", "-C", args.repo, "-c", "core.quotePath=false", "diff",
                                 "--no-color", "--no-ext-diff", f"{args.base}..{args.head}"],
                                capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise SystemExit(f"git diff 실패: {result.stderr.strip()}")
        text = result.stdout
        commits = commits_in_range(args.repo, f"{args.base}..{args.head}")

        def read_file(path):
            shown = subprocess.run(["git", "-C", args.repo, "show", f"{args.head}:{path}"],
                                   capture_output=True, text=True, encoding="utf-8")
            return shown.stdout if shown.returncode == 0 else ""
    else:
        parser.error("--base 또는 --diff 가운데 하나가 필요하다")
    print_table(count(parse_diff(text), commits, read_file), args.markdown, args.label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
