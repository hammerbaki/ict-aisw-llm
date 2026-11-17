"""관측 도구의 테스트."""

import json

from ops.telemetry import logparse, pii_scan, report


def test_parse_line_with_quoted_value_and_numbers():
    line = ('2027-09-08 14:03:47 ERROR jobprep.api path=/api/summary status=503 '
            'error=LLMError detail="LLM 호출에 실패하였다: RateLimitError"')
    record = logparse.parse_line(line)
    assert record["ts"] == "2027-09-08T14:03:47"
    assert record["level"] == "ERROR"
    assert record["status"] == 503
    assert record["detail"] == "LLM 호출에 실패하였다: RateLimitError"


def test_parse_line_rejects_other_format():
    assert logparse.parse_line("아무 형식도 아닌 줄") is None


def test_percentile_nearest_rank():
    values = list(range(1, 101))
    assert report.percentile(values, 50) == 50
    assert report.percentile(values, 95) == 95
    assert report.percentile([], 95) is None


def test_route_groups_ids():
    assert report.route("/api/jobs/12") == "/api/jobs/{id}"
    assert report.route("/api/jobs") == "/api/jobs"


def test_cost_of_known_and_unknown_model():
    prices = {"m": {"input_per_mtok": 1.0, "output_per_mtok": 5.0}}
    assert abs(report.cost_of("m", 1_000_000, 200_000, prices) - 2.0) < 1e-9
    assert report.cost_of("x", 10, 10, prices) is None


def test_budget_exit_code(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "llm.log").write_text(
        "2027-09-06 09:06:51 INFO jobprep.llm task=summary model=claude-haiku-5-5 "
        "input_tokens=1000000 output_tokens=1000000\n", encoding="utf-8")
    args = ["--logs", str(logs), "--loop", str(tmp_path / "none"), "--multi", str(tmp_path / "none")]
    assert report.main(args + ["--budget-usd", "1.0"]) == 0      # 0.60 USD: 예산 안
    assert report.main(args + ["--budget-usd", "0.5"]) == 2      # 예산 초과


def test_loop_section_counts_success_handoff_and_suspect():
    rows = [
        {"event": "start", "run_id": "a", "config": {"protected": ["tests/"]}},
        {"event": "attempt", "run_id": "a", "turns": 5, "decision": "commit", "changed": ["api/jobs.py"]},
        {"event": "end", "run_id": "a", "status": "green", "attempts": 1, "spent_usd": 0.2},
        {"event": "attempt", "run_id": "b", "turns": 9, "decision": "restore", "changed": ["api/jobs.py"]},
        {"event": "attempt", "run_id": "b", "turns": 9, "decision": "restore", "changed": ["api/jobs.py"]},
        {"event": "end", "run_id": "b", "status": "gave_up", "attempts": 2, "spent_usd": 0.4},
        {"event": "start", "run_id": "c", "config": {"protected": ["tests/"]}},
        {"event": "attempt", "run_id": "c", "turns": 3, "decision": "commit", "changed": ["tests/test_jobs.py"]},
        {"event": "end", "run_id": "c", "status": "green", "attempts": 1, "spent_usd": 0.1},
    ]
    lines, spent = report.loop_section(rows)
    text = "\n".join(lines)
    assert "검증된 작업 성공률 33%" in text
    assert "green만 세면 67%" in text
    assert "c(tests/test_jobs.py)" in text
    assert "b(gave_up)" in text
    assert abs(spent - 0.7) < 1e-9


def test_multi_section_reads_events_and_agent_outputs(tmp_path):
    """10장 형식: ops/multi/logs/<이슈>/events.jsonl과 <작업>_시도<n>.out(Claude Code의 JSON 결과)."""
    def event(issue, actor, name, task="", detail=""):
        return json.dumps({"time": "2027-11-15T10:00:00", "issue": issue, "actor": actor, "event": name,
                           "task": task, "detail": detail}, ensure_ascii=False)
    a = tmp_path / "ISSUE-01"
    a.mkdir()
    (a / "events.jsonl").write_text("\n".join([
        event("ISSUE-01", "implementer:T1", "dispatched", "T1", "attempt=1 cmd=bash"),
        event("ISSUE-01", "judge", "judged", "T1", "verdict=거부 commit=aaaaaaa"),
        event("ISSUE-01", "implementer:T1", "dispatched", "T1", "attempt=2 cmd=bash"),
        event("ISSUE-01", "judge", "judged", "T1", "verdict=통과 commit=bbbbbbb"),
        event("ISSUE-01", "human", "merged", "T1", "commit=ccccccc"),
    ]) + "\n", encoding="utf-8")
    (a / "T1_시도1.out").write_text(json.dumps({"total_cost_usd": 0.3, "num_turns": 5}) + "\n", encoding="utf-8")
    (a / "T1_시도2.out").write_text("가짜 에이전트의 글 출력\n", encoding="utf-8")
    b = tmp_path / "ISSUE-02"
    b.mkdir()
    (b / "events.jsonl").write_text("\n".join([
        event("ISSUE-02", "implementer:T1", "dispatched", "T1", "attempt=1 cmd=bash"),
        event("ISSUE-02", "judge", "judged", "T1", "verdict=통과 commit=ddddddd"),
        event("ISSUE-02", "human", "merge_conflict", "T1", "files=api/main.py "),
    ]) + "\n", encoding="utf-8")
    runs = report.read_multi(tmp_path)
    assert sorted(runs) == ["ISSUE-01", "ISSUE-02"]
    lines, spent = report.multi_section(runs, [])
    text = "\n".join(lines)
    assert "이슈 2건, 작업 2개, 예외 처리 없이 병합 1건, 그 밖 ISSUE-02(미완료)" in text
    assert "시도 3회(재시도율 50%), 판정 3회 가운데 거부 1회" in text
    assert "계획된 병합 1회, 예외 처리 1회 (merge_conflict 1)" in text
    assert "구현 에이전트 출력 2개 가운데 비용이 있는 1개" in text
    assert abs(spent - 0.3) < 1e-9


def test_multi_section_orca_route_without_dispatch(tmp_path):
    """10장 핵심 실습(Orca 작업 공간)의 기록: 조정 스크립트를 쓰지 않아 dispatched가 없고 judge.sh·merge.sh만 남긴다."""
    def event(name, task, detail):
        return json.dumps({"time": "2027-11-20T10:00:00", "issue": "ISSUE-07", "actor": "judge" if name == "judged" else "human",
                           "event": name, "task": task, "detail": detail}, ensure_ascii=False)
    a = tmp_path / "ISSUE-07"
    a.mkdir()
    (a / "events.jsonl").write_text("\n".join([
        event("judged", "T1", "verdict=통과 commit=aaaaaaa"),
        event("judged", "T2", "verdict=거부 commit=bbbbbbb"),
        event("judged", "T2", "verdict=통과 commit=ccccccc"),
        event("merged", "T1", "commit=ddddddd"),
        event("merge_conflict", "T2", "files=docs/요구사항명세서.md "),
        event("merged", "T2", "commit=eeeeeee"),
    ]) + "\n", encoding="utf-8")
    lines, spent = report.multi_section(report.read_multi(tmp_path), [])
    text = "\n".join(lines)
    assert "이슈 1건, 작업 2개, 예외 처리 없이 병합 0건, 그 밖 ISSUE-07(예외 처리 뒤 병합)" in text
    assert "시도 3회(재시도율 50%), 판정 3회 가운데 거부 1회" in text
    assert "실행 사건(dispatched)이 없는 이슈 1건(ISSUE-07)" in text
    assert "비용: 구현 에이전트 출력 0개에 비용이 없다" in text
    assert spent == 0


def test_parse_trailers_keeps_agent_commits_only():
    text = ("abc1234\x1fimplementer\x1fISSUE-07/T2\x1f2\x1e\n"
            "def5678\x1f\x1f\x1f\x1e\n"
            "0a1b2c3\x1fimplementer\x1fISSUE-07/T1\x1f1\x1e\n")
    commits = report.parse_trailers(text)
    assert [c["commit"] for c in commits] == ["abc1234", "0a1b2c3"]
    assert commits[0]["attempt"] == 2
    lines, _ = report.multi_section({"ISSUE-07": {"events": [], "outs": []}}, commits)
    assert "Agent-Task가 붙은 커밋 2건(implementer 2), 두 번째 이후 시도의 커밋 1건" in "\n".join(lines)


def test_pii_scan_finds_and_masks(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("question=연락은 010-1234-5678 로\nok=1\n", encoding="utf-8")
    results = pii_scan.scan_paths([tmp_path])
    assert len(results) == 1
    assert results[0][1] == "휴대전화"
    assert "5678" not in results[0][3]


def test_sample_logs_have_no_pii():
    """기준 저장소의 운영 기록 견본에는 개인 정보 꼴이 없다."""
    assert pii_scan.scan_paths(["logs"]) == []
