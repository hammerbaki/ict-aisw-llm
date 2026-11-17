"""check_design.py의 테스트. 키트 폴더에서 `pytest -q`로 실행한다."""
import shutil
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
import check_design  # noqa: E402

SPEC = """# 요구사항 명세서

## 2. 기능 요구

| ID | 문형 | 요구 |
|---|---|---|
| REQ-001 | 상시 | 시스템은 공고 목록을 표시해야 한다. |
| REQ-002 | 사건 | 사용자가 공고를 고르면, 시스템은 상세를 표시해야 한다. |

## 3. 비기능 요구

| ID | 문형 | 요구 |
|---|---|---|
| REQ-003 | 상시 | 시스템은 키보드로 조작할 수 있어야 한다. |

## 4. 화면 목록

| 화면 ID | 화면 이름 | 목적 | 관련 요구 | 진입 흐름 |
|---|---|---|---|---|
| SCR-01 | 공고 목록 | 찾기 | REQ-001 | FLOW-01 |
| SCR-02 | 공고 상세 | 읽기 | REQ-002 | FLOW-01 |
"""

IA = """# 정보 구조

```mermaid
flowchart TD
    A["SCR-01 공고 목록"] --> B["SCR-02 공고 상세"]
```
"""

FLOW = """# 사용자 흐름

## FLOW-01

```mermaid
flowchart TD
    S(["시작"]) --> A["SCR-01 공고 목록"]
    A --> B["SCR-02 공고 상세 (REQ-002)"]
```
"""

JOURNEY = """# 여정 지도

## 여정 지도

| 구분 | 1. 탐색 | 2. 판단 |
|---|---|---|
| 행동 | 앱을 본다 [근거: 인터뷰_01:L11] | 요건을 읽는다 [가정] |
| 기회 | 목록 (REQ-001 → SCR-01) | 요약 |

## 가정과 확인할 것

| 번호 | 가정 | 확인 방법 |
|---|---|---|
| 1 | 근거 표시가 없어도 이 표는 검사하지 않는다 | 인터뷰 |
"""


def make_docs(tmp_path, spec=SPEC, ia=IA, flow=FLOW, journey=JOURNEY):
    docs = tmp_path / "docs"
    (docs / "설계").mkdir(parents=True)
    (docs / "요구사항명세서.md").write_text(spec, encoding="utf-8")
    (docs / "설계" / "정보구조.md").write_text(ia, encoding="utf-8")
    (docs / "설계" / "사용자흐름.md").write_text(flow, encoding="utf-8")
    if journey is not None:
        (docs / "설계" / "여정지도.md").write_text(journey, encoding="utf-8")
    return docs


def run(docs):
    lines = []
    errors, warnings = check_design.run(docs, out=lines.append)
    return errors, warnings, lines


def test_good_set_passes(tmp_path):
    errors, warnings, lines = run(make_docs(tmp_path))
    assert errors == [] and warnings == []
    assert "오류 0건, 경고 0건" in lines


def test_v1_spec_without_screen_list_fails(tmp_path):
    v1 = (KIT / "기준산출물" / "jobprep" / "docs" / "요구사항명세서.md").read_text(encoding="utf-8")
    errors, _, _ = run(make_docs(tmp_path, spec=v1))
    assert "명세서에 「## 화면 목록」 절이 없다" in errors


def test_unknown_screen_in_sitemap(tmp_path):
    ia = IA + '\n    B --> C["SCR-12 지원 현황"]\n'
    errors, _, _ = run(make_docs(tmp_path, ia=ia))
    assert "정보구조.md: 화면 목록에 없는 화면 ID SCR-12" in errors


def test_unknown_requirement_in_screen_list(tmp_path):
    spec = SPEC.replace("| REQ-002 | FLOW-01 |", "| REQ-002, REQ-099 | FLOW-01 |")
    errors, _, _ = run(make_docs(tmp_path, spec=spec))
    assert "SCR-02: 명세에 없는 요구 ID REQ-099" in errors


def test_unknown_requirement_in_flow(tmp_path):
    flow = FLOW.replace("(REQ-002)", "(REQ-020)")
    errors, _, _ = run(make_docs(tmp_path, flow=flow))
    assert "사용자흐름.md: 명세에 없는 요구 ID REQ-020" in errors


def test_screen_without_requirement(tmp_path):
    spec = SPEC.replace("| SCR-02 | 공고 상세 | 읽기 | REQ-002 |", "| SCR-02 | 공고 상세 | 읽기 | - |")
    errors, warnings, _ = run(make_docs(tmp_path, spec=spec))
    assert "SCR-02: 화면 목록에 관련 요구가 없다" in errors
    assert "REQ-002: 어느 화면에도 연결되지 않은 기능 요구" in warnings


def test_duplicate_screen_id(tmp_path):
    spec = SPEC + "| SCR-02 | 공고 상세 2 | 읽기 | REQ-002 | - |\n"
    errors, _, _ = run(make_docs(tmp_path, spec=spec))
    assert "화면 ID가 화면 목록에 두 번 나온다: SCR-02" in errors


def test_nonfunctional_requirement_needs_no_screen(tmp_path):
    _, warnings, _ = run(make_docs(tmp_path))
    assert not any("REQ-003" in w for w in warnings)


def test_screen_missing_from_sitemap_is_warning(tmp_path):
    ia = IA.replace(' --> B["SCR-02 공고 상세"]', "")
    errors, warnings, _ = run(make_docs(tmp_path, ia=ia))
    assert errors == []
    assert "SCR-02: 사이트맵(정보구조.md)에 없는 화면" in warnings


@pytest.mark.parametrize("cell", ["요건을 읽는다", "요건을 읽는다 [근거: ]", "요건을 읽는다 [근거]"])
def test_journey_cell_without_evidence(tmp_path, cell):
    journey = JOURNEY.replace("요건을 읽는다 [가정]", cell)
    _, warnings, _ = run(make_docs(tmp_path, journey=journey))
    assert warnings == ["여정지도.md 「행동」 행 2번째 단계: 근거 표시가 없다"]


def test_missing_journey_is_warning(tmp_path):
    _, warnings, _ = run(make_docs(tmp_path, journey=None))
    assert warnings == ["설계/여정지도.md가 없어 근거 표시를 검사하지 않았다"]


def test_heading_inside_code_block_is_ignored(tmp_path):
    spec = SPEC.replace("## 3. 비기능 요구", "```text\n## 화면 목록\n```\n\n## 3. 비기능 요구")
    errors, _, _ = run(make_docs(tmp_path, spec=spec))
    assert errors == []


def test_missing_file(tmp_path):
    docs = make_docs(tmp_path)
    (docs / "설계" / "사용자흐름.md").unlink()
    errors, _, _ = run(docs)
    assert any("파일이 없다" in e for e in errors)


def test_main_exit_codes(tmp_path, capsys):
    docs = make_docs(tmp_path)
    assert check_design.main([str(docs)]) == 0
    assert "결과: 통과" in capsys.readouterr().out
    (docs / "설계" / "여정지도.md").unlink()
    assert check_design.main([str(docs)]) == 0
    assert check_design.main([str(docs), "--strict"]) == 1
    shutil.rmtree(docs / "설계")
    assert check_design.main([str(docs)]) == 1


def test_screen_list_without_ids(tmp_path):
    spec = SPEC.split("## 4. 화면 목록")[0] + "## 4. 화면 목록\n\n(아직 비어 있음)\n"
    errors, warnings, lines = run(make_docs(tmp_path, spec=spec))
    assert errors == ["화면 목록 표에서 화면 ID(SCR-01 형식)를 하나도 찾지 못하였다"]
    assert "[검사] 화면 목록이 없어 나머지 검사를 하지 않았다" in lines


def test_quality_subsection_is_nonfunctional(tmp_path):
    spec = SPEC.replace("## 3. 비기능 요구", "## 3. 요구 문장 (EARS)\n\n### 공통 품질 요구")
    errors, warnings, lines = run(make_docs(tmp_path, spec=spec))
    assert errors == [] and warnings == []
    assert "[검사] 요구사항명세서.md: 요구 3개(기능 요구 2개), 화면 2개" in lines
