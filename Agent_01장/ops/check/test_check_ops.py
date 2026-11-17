"""check_ops.py의 테스트. 저장소 폴더에서 `pytest -q ops/check`로 실행한다.

jobprep의 `pytest -q`(tests/ 폴더만 모은다)에는 들어가지 않는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ops  # noqa: E402

HEAD = "| ID | 분류 | 문형 | 요구 | 측정 방법 | 확인하는 장 |\n|---|---|---|---|---|---|\n"


def row(rid, cat, form, req, meas="`pytest -q` 결과", ch="2"):
    return f"| {rid} | {cat} | {form} | {req} | {meas} | {ch} |\n"


def good_table(n_each=4):
    rows = []
    samples = {
        "SEC": ("보안", "상시", "운영 에이전트는 `.env` 파일을 읽지 않아야 한다."),
        "REL": ("신뢰성", "원치 않는 상황", "만약 LLM 호출이 실패하면, 시스템은 503으로 응답해야 한다."),
        "CON": ("일관성", "이벤트", "운영 에이전트가 요구를 구현하면, 운영 에이전트는 명세서의 상태 열을 고쳐야 한다."),
        "REP": ("재현성", "선택", "모의 모드가 설정된 경우, 시스템은 같은 입력에 같은 응답을 내야 한다."),
    }
    for code, (cat, form, req) in samples.items():
        for i in range(1, n_each + 1):
            rows.append(row(f"OR-{code}-{i:02d}", cat, form, req))
    return HEAD + "".join(rows)


def test_good_spec_passes():
    errors, warnings, s = check_ops.check_reqs(good_table())
    assert errors == []
    assert s["total"] == 16 and s["SEC"] == 4


def test_too_few_requirements_fails():
    errors, _, s = check_ops.check_reqs(good_table(n_each=3))
    assert s["total"] == 12
    assert any("15개 이상" in e for e in errors)


def test_category_minimum_is_checked():
    text = good_table() + row("OR-SEC-05", "보안", "상시", "시스템은 키를 내보내지 않아야 한다.")
    errors, _, _ = check_ops.check_reqs(text, min_total=15, min_each=5)
    assert any("신뢰성(REL) 요건이 4개" in e for e in errors)


def test_bad_id_and_duplicate():
    text = good_table() + row("SEC-9", "보안", "상시", "시스템은 키를 내보내지 않아야 한다.")
    text += row("OR-SEC-01", "보안", "상시", "시스템은 키를 내보내지 않아야 한다.")
    errors, _, _ = check_ops.check_reqs(text)
    assert any("SEC-9" in e and "ID 형식" in e for e in errors)
    assert any("OR-SEC-01" in e and "겹친다" in e for e in errors)


def test_category_must_match_id():
    text = good_table() + row("OR-REL-09", "보안", "상시", "시스템은 기록을 남겨야 한다.")
    errors, _, _ = check_ops.check_reqs(text)
    assert any("OR-REL-09" in e and "맞지 않는다" in e for e in errors)


def test_unknown_category():
    text = good_table() + row("OR-SEC-09", "가용성", "상시", "시스템은 기록을 남겨야 한다.")
    errors, _, _ = check_ops.check_reqs(text)
    assert any("가용성" in e for e in errors)


def test_measurement_must_not_be_empty():
    text = good_table()
    text += row("OR-SEC-09", "보안", "상시", "시스템은 키를 내보내지 않아야 한다.", meas="")
    text += row("OR-SEC-10", "보안", "상시", "시스템은 키를 내보내지 않아야 한다.", meas="미정")
    text += row("OR-SEC-11", "보안", "상시", "시스템은 키를 내보내지 않아야 한다.", meas="「무엇을 어떻게 재는가」")
    errors, _, _ = check_ops.check_reqs(text)
    for rid in ("OR-SEC-09", "OR-SEC-10", "OR-SEC-11"):
        assert any(rid in e and "측정 방법" in e for e in errors), rid


def test_missing_measurement_column():
    text = "| ID | 분류 | 문형 | 요구 |\n|---|---|---|---|\n| OR-SEC-01 | 보안 | 상시 | 시스템은 키를 내보내지 않아야 한다. |\n"
    errors, _, _ = check_ops.check_reqs(text)
    assert any("「측정 방법」 칸이 없다" in e for e in errors)


def test_ears_markers():
    text = good_table()
    text += row("OR-REL-09", "신뢰성", "원치 않는 상황", "LLM 호출이 실패하면, 시스템은 503으로 응답해야 한다.")
    text += row("OR-REL-10", "신뢰성", "상태", "시스템은 모의 모드에서 API를 부르지 않아야 한다.")
    text += row("OR-REL-11", "신뢰성", "조건", "시스템은 기록을 남겨야 한다.")
    text += row("OR-REL-12", "신뢰성", "상시", "시스템은 빠르게 응답한다.")
    errors, warnings, _ = check_ops.check_reqs(text)
    assert any("OR-REL-09" in e and "만약" in e for e in errors)
    assert any("OR-REL-10" in e and "동안" in e for e in errors)
    assert any("OR-REL-11" in e and "문형" in e for e in errors)
    assert any("OR-REL-12" in e and "끝나지 않는다" in e for e in errors)
    assert any("OR-REL-12" in e and "빠르게" in w for w in warnings for e in [w])


def test_non_requirement_tables_are_ignored():
    text = "| 분류 | 뜻 |\n|---|---|\n| 보안 | 허용된 일만 한다 |\n\n" + good_table()
    errors, _, s = check_ops.check_reqs(text)
    assert errors == [] and s["total"] == 16


ROLE = """### R{n} {name}

| 항목 | 내용 |
|---|---|
| 권한 | {perm} |
| 입력 | 이슈 |
| 출력 | 계획 문서 |
| 완료 조건 | {done} |
| 사람 승인 지점 | 계획을 사람이 승인한다 |
| 관련 운영 요건 | {reqs} |
"""


def roles_text(k=5, perm="읽기: 저장소 전체. 금지: 파일 수정", done="계획이 승인되었다", reqs="OR-SEC-01"):
    return "# 역할 정의\n\n" + "\n".join(
        ROLE.format(n=i, name=f"역할{i}", perm=perm, done=done, reqs=reqs) for i in range(1, k + 1))


def test_roles_pass():
    errors, warnings, s = check_ops.check_roles(roles_text(), {"OR-SEC-01"})
    assert errors == [] and warnings == [] and s["roles"] == 5


def test_roles_minimum():
    errors, _, _ = check_ops.check_roles(roles_text(k=4))
    assert any("역할이 4개" in e for e in errors)


def test_role_empty_field_and_unknown_req():
    errors, _, _ = check_ops.check_roles(roles_text(done="「무엇이 되면 끝인가」", reqs="OR-SEC-01, OR-REL-07"), {"OR-SEC-01"})
    assert any("완료 조건" in e and "비어 있다" in e for e in errors)
    assert any("OR-REL-07" in e for e in errors)


def test_role_without_prohibition_warns():
    errors, warnings, _ = check_ops.check_roles(roles_text(perm="읽기: 저장소 전체"))
    assert errors == []
    assert len(warnings) == 5 and "금지" in warnings[0]


def test_cli_exit_codes(tmp_path, capsys):
    good = tmp_path / "운영요건.md"
    good.write_text(good_table(), encoding="utf-8")
    assert check_ops.main(["reqs", str(good)]) == 0
    bad = tmp_path / "나쁜.md"
    bad.write_text(good_table(n_each=2), encoding="utf-8")
    assert check_ops.main(["reqs", str(bad)]) == 1
    roles = tmp_path / "역할정의.md"
    roles.write_text(roles_text(), encoding="utf-8")
    assert check_ops.main(["roles", str(roles), "--reqs", str(good)]) == 0
    out = capsys.readouterr().out
    assert "결과: 통과" in out and "오류 " in out


def test_escaped_pipe_in_cell_is_not_a_column():
    meas = r"`git ls-files \| grep -cx .env` 결과가 0"
    text = good_table() + row("OR-SEC-09", "보안", "상시", "시스템은 키를 커밋에 넣지 않아야 한다.", meas=meas)
    errors, _, s = check_ops.check_reqs(text)
    assert errors == [] and s["SEC"] == 5
