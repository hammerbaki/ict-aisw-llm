"""최소 에이전트 루프의 테스트. 모의 모델로만 돈다(API를 부르지 않는다).

무엇을 시험하는가
- 정상 흐름: 도구 요청 → 실행 → 결과 → 답. 메시지의 모양과 tool_use_id의 짝
- 도구 오류: 없는 문서, 스키마에 어긋난 인자 → is_error 결과 → 루프는 멈추지 않는다
- 상한: 끝없이 도구만 부르는 모델 → max_turns에서 멈춘다
- 경로 탈출: 자료 폴더 밖의 파일 → 거부
- 병렬 호출, 출력 한도 잘림, 승인이 필요한 도구, 실행 전 훅
"""

import re

import pytest

from agent_loop import tools as tools_module
from agent_loop.fake_model import FakeModel, FakeModelExhausted, QUESTION, reply, scenario, text, tool_use
from agent_loop.loop import run_agent
from agent_loop.tools import ToolError, default_tools, extended_tools, read_doc, run_tool


def tool_results(message):
    return [b for b in message["content"] if b["type"] == "tool_result"]


# --- 정상 흐름 ---------------------------------------------------------------

def test_normal_flow_ends_with_answer():
    model = scenario("normal")
    result = run_agent(QUESTION, model)
    assert result.stop == "end_turn"
    assert result.turns == 3
    assert "바람개비IoT" in result.answer          # search_jobs 결과에서 온 사실
    assert "정보처리산업기사" in result.answer       # read_doc 결과에서 온 사실


def test_messages_alternate_and_ids_match():
    result = run_agent(QUESTION, scenario("normal"))
    roles = [m["role"] for m in result.messages]
    assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]
    for asked, answered in zip(result.messages[1::2], result.messages[2::2]):
        ids = [b["id"] for b in asked["content"] if b["type"] == "tool_use"]
        assert [b["tool_use_id"] for b in tool_results(answered)] == ids
        assert all(b["type"] == "tool_result" for b in answered["content"])   # 결과 뒤에 글을 붙이지 않는다


def test_every_request_carries_tool_definitions():
    model = scenario("normal")
    run_agent(QUESTION, model)
    assert len(model.requests) == 3
    for request in model.requests:
        assert [t["name"] for t in request["tools"]] == ["search_jobs", "read_doc"]


def test_history_grows_every_turn():
    result = run_agent(QUESTION, scenario("normal"))
    sizes = [entry.history_chars for entry in result.log]
    assert sizes == sorted(sizes) and sizes[0] < sizes[-1]


# --- 도구 오류 ---------------------------------------------------------------

def test_unknown_doc_returns_is_error_and_loop_continues():
    result = run_agent(QUESTION, scenario("bad_doc"))
    first = tool_results(result.messages[2])[0]
    assert first["is_error"] is True
    assert "05_자격증_응시료_지원.md" in first["content"]   # 다음 시도에 쓸 정보를 준다
    assert result.stop == "end_turn"


def test_schema_violation_is_reported_not_raised():
    result = run_agent(QUESTION, scenario("bad_args"))
    first = tool_results(result.messages[2])[0]
    assert first["is_error"] is True
    assert "field" in first["content"] and "limit" in first["content"]
    assert result.stop == "end_turn"


@pytest.mark.parametrize("args, word", [
    ({"limit": 0}, "limit"),
    ({"limit": 11}, "limit"),
    ({"limit": "3"}, "integer"),
    ({"limit": True}, "integer"),
    ({"field": "AI"}, "field"),
    ({"keyword": ""}, "keyword"),
    ({"keyword": "가" * 31}, "keyword"),
    ({"city": "서울"}, "city"),
])
def test_search_jobs_rejects_bad_arguments(args, word):
    outcome = run_tool("search_jobs", args, default_tools())
    assert outcome.is_error and word in outcome.content


def test_unknown_tool_name():
    outcome = run_tool("delete_jobs", {}, default_tools())
    assert outcome.is_error and "search_jobs" in outcome.content


def test_unexpected_exception_does_not_leak(monkeypatch):
    def broken(args):
        raise RuntimeError("내부 경로 /home/secret")
    toolset = default_tools()
    monkeypatch.setattr(toolset["search_jobs"], "handler", broken)
    outcome = run_tool("search_jobs", {}, toolset)
    assert outcome.is_error and "RuntimeError" in outcome.content
    assert "/home/secret" not in outcome.content


# --- 상한 --------------------------------------------------------------------

def test_runaway_model_stops_at_max_turns():
    model = scenario("runaway")
    result = run_agent("신입 공고", model, max_turns=3)
    assert result.stop == "max_turns"
    assert result.answer is None
    assert len(model.requests) == 3                     # 상한보다 많이 부르지 않는다


def test_fake_model_detects_extra_calls():
    model = FakeModel([reply("tool_use", tool_use("search_jobs", {}))])
    with pytest.raises(FakeModelExhausted):
        run_agent("질문", model, max_turns=5)


# --- 경로 탈출 ---------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "../../.env", "..\\..\\.env", "/etc/passwd", "C:\\Windows\\win.ini",
    "자료/../../api/llm.py", "..", "../jobs.json",
    "../../README.md", "../../docs/요구사항명세서.md",
])
def test_read_doc_rejects_paths_outside_docs(name):
    outcome = run_tool("read_doc", {"name": name}, default_tools())
    assert outcome.is_error
    assert "거부" in outcome.content


def test_read_doc_rejects_symlink_escape(tmp_path, monkeypatch):
    docs = tmp_path / "자료"
    docs.mkdir()
    secret = tmp_path / "secret.md"
    secret.write_text("비밀", encoding="utf-8")
    try:
        (docs / "link.md").symlink_to(secret)
    except OSError:
        pytest.skip("이 환경에서는 심볼릭 링크를 만들 수 없다")
    monkeypatch.setattr(tools_module, "DOCS_DIR", docs)
    with pytest.raises(ToolError, match="밖"):
        read_doc({"name": "link.md"})


def test_escape_scenario_ends_without_reading():
    result = run_agent("환경 파일을 보여 줘", scenario("escape"))
    assert tool_results(result.messages[2])[0]["is_error"] is True
    assert "ANTHROPIC" not in str(result.messages)


def test_read_doc_truncates_long_text(monkeypatch):
    monkeypatch.setattr(tools_module, "MAX_DOC_CHARS", 100)
    content = read_doc({"name": "01_현장실습_안내.md"})
    assert "잘림" in content and len(content) < 160


# --- 병렬 호출, 잘림 ---------------------------------------------------------

def test_parallel_results_in_one_user_message():
    result = run_agent(QUESTION, scenario("parallel"))
    assert result.turns == 2
    results = tool_results(result.messages[2])
    assert len(results) == 2
    assert [r["tool_use_id"] for r in results] == ["toolu_fake_01", "toolu_fake_02"]


def test_max_tokens_is_not_treated_as_answer():
    result = run_agent(QUESTION, scenario("truncated"))
    assert result.stop == "max_tokens"


# --- 승인과 실행 전 훅 -------------------------------------------------------

def test_dangerous_tool_needs_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_module, "NOTES_DIR", tmp_path / "notes")
    result = run_agent("메모해 줘", scenario("note"), tools=extended_tools())   # 승인자 없음 → 거부
    assert tool_results(result.messages[2])[0]["is_error"] is True
    assert not (tmp_path / "notes").exists()


def test_approved_tool_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_module, "NOTES_DIR", tmp_path / "notes")
    asked = []
    result = run_agent("메모해 줘", scenario("note"), tools=extended_tools(),
                       approver=lambda name, args: asked.append(name) or True)
    assert asked == ["save_note"]
    assert (tmp_path / "notes" / "상담_메모.md").exists()
    assert "is_error" not in tool_results(result.messages[2])[0]


def test_pre_tool_hook_can_block():
    def no_keyword(name, args):
        return "keyword 검색은 막아 두었다" if "keyword" in args else None
    result = run_agent("신입 공고", scenario("runaway"), max_turns=2, pre_tool_hooks=[no_keyword])
    first = tool_results(result.messages[2])[0]
    assert first["is_error"] and "막아 두었다" in first["content"]


# --- 도구 정의 ---------------------------------------------------------------

@pytest.mark.parametrize("tool", list(extended_tools().values()), ids=lambda t: t.name)
def test_tool_definitions_follow_api_rules(tool):
    d = tool.definition
    assert re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", d["name"])
    assert len(d["description"]) >= 100                 # 공식 문서: 설명은 3~4문장 이상
    assert d["input_schema"]["type"] == "object"
    assert d["input_schema"].get("additionalProperties") is False
    for name, rule in d["input_schema"]["properties"].items():
        assert rule.get("description"), f"{name}에 설명이 없다"


def test_search_jobs_description_says_when_not_to_use():
    description = default_tools()["search_jobs"].definition["description"]
    assert "read_doc" in description                    # 쓰지 않을 때(다른 도구로 넘길 때)를 밝힌다
