"""count_violations.py의 테스트: diff에서 규칙 위반을 센다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from count_violations import count, parse_diff  # noqa: E402


def make_diff(changes):
    """{경로: [더한 줄]}로 최소한의 unified diff 글을 만든다."""
    parts = []
    for path, lines in changes.items():
        parts.append(f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1,0 +1,{len(lines)} @@")
        parts.extend("+" + line for line in lines)
    return "\n".join(parts) + "\n"


def totals(changes, commits=None):
    return {rid: len(found) for rid, _, found in count(parse_diff(make_diff(changes)), commits)}


def test_parse_diff_reads_added_lines_and_korean_paths():
    files = parse_diff(make_diff({"docs/요구사항명세서.md": ["| REQ-SUM-06 |"], "api/x.py": ["a", "b"]}))
    assert files == {"docs/요구사항명세서.md": ["| REQ-SUM-06 |"], "api/x.py": ["a", "b"]}


def test_parse_diff_ignores_removed_and_header_lines():
    text = "diff --git a/api/x.py b/api/x.py\n--- a/api/x.py\n+++ b/api/x.py\n@@ -1 +1 @@\n-old\n+new\n"
    assert parse_diff(text) == {"api/x.py": ["new"]}


def test_llm_direct_call_outside_llm_module():
    result = totals({"api/summary.py": ["import anthropic"], "api/llm.py": ["import anthropic"]})
    assert result["R1"] == 1


def test_model_name_literal_print_and_inner_html():
    result = totals({
        "api/summary.py": ['MODEL = "claude-haiku-5-5"', '    print("debug")', '    logger.info("x")'],
        "web/js/job.js": ["box.innerHTML = text;", "box.textContent = text;"],
    })
    assert (result["R2"], result["R3"], result["R4"]) == (1, 1, 1)


def test_pprint_and_method_named_print_are_not_counted():
    result = totals({"api/a.py": ["    pprint(x)", "    report.print(x)"]})
    assert result["R3"] == 0


def test_protected_paths_and_secrets():
    result = totals({"data/jobs.json": ["{}"], ".env": ["ANTHROPIC_API_KEY=sk-ant-abcdefghijk"],
                     ".env.example": ["ANTHROPIC_API_KEY="]})
    assert result["R5"] == 2
    assert result["R6"] == 1


def test_code_without_tests_and_spec():
    result = totals({"api/summary.py": ["x = 1"]})
    assert (result["R7"], result["R8"]) == (1, 1)
    result = totals({"api/summary.py": ["x = 1"], "tests/test_summary.py": ['@pytest.mark.req(id="REQ-SUM-06")', "def test_a():"],
                     "docs/요구사항명세서.md": ["| REQ-SUM-06 |"]})
    assert (result["R7"], result["R8"], result["R9"]) == (0, 0, 0)


def test_new_test_without_req_marker():
    result = totals({"tests/test_a.py": ["def test_a():", "    assert True", "", "", "", "def test_b():"]})
    assert result["R9"] == 2


def test_req_marker_on_function_or_module():
    decorated = totals({"tests/test_a.py": ['@pytest.mark.req(id="REQ-JOB-04")', "def test_a(client):", "",
                                           "def test_b(client):"]})
    assert decorated["R9"] == 1
    module = totals({"tests/test_b.py": ['pytestmark = pytest.mark.req(id="REQ-SUM-06")', "", "def test_a():",
                                        "def test_b():"]})
    assert module["R9"] == 0


def test_module_marker_found_in_whole_file():
    files = parse_diff(make_diff({"tests/test_c.py": ["def test_new():", "    assert True"]}))
    rows = count(files, read_file=lambda path: 'pytestmark = pytest.mark.req(id="REQ-ASK-06")\n')
    assert {rid: len(f) for rid, _, f in rows}["R9"] == 0


def test_commit_messages_are_counted_only_when_given():
    assert "R10" not in totals({"README.md": ["x"]})
    result = totals({"README.md": ["x"]}, commits=[("a1", "docs: 설명 추가"), ("b2", "설명 추가")])
    assert result["R10"] == 1


def test_sample_diffs_in_kit():
    kit = Path(__file__).resolve().parents[3] / "견본" / "비교"
    if not kit.exists():  # 저장소에 복사한 뒤에는 견본이 없다
        return
    without = sum(len(f) for _, _, f in count(parse_diff((kit / "규칙없음.diff").read_text(encoding="utf-8"))))
    with_rules = sum(len(f) for _, _, f in count(parse_diff((kit / "규칙있음.diff").read_text(encoding="utf-8"))))
    assert (without, with_rules) == (4, 1)
