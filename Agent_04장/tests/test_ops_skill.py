# -*- coding: utf-8 -*-
"""4장: 장애 보고서 스킬(incident-report)의 스크립트와 SKILL.md 형식 테스트.

스킬 폴더는 두 곳 가운데 있는 곳을 쓴다.
- 4장 2단계(스킬): .claude/skills/incident-report/
- 4장 3단계(플러그인): plugins/jobprep-ops/skills/incident-report/
스크립트의 동작은 저장소의 logs/ 견본으로 확인하고, SKILL.md는 형식만 본다.
보고서 내용이 맞는지는 사람이 판정한다.
"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    ROOT / "plugins" / "jobprep-ops" / "skills" / "incident-report",
    ROOT / ".claude" / "skills" / "incident-report",
]
LOGS = ROOT / "logs"


def skill_dir():
    for d in CANDIDATES:
        if (d / "scripts").is_dir():
            return d
    pytest.fail("incident-report 스킬 폴더(scripts/ 포함)가 .claude/skills/나 plugins/jobprep-ops/skills/에 없다")


def load(name):
    path = skill_dir() / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------- log_summary.py ----------

def test_기록_한_줄을_칸으로_나눈다():
    s = load("log_summary")
    rec = s.parse_line('2027-09-08 14:03:47 ERROR jobprep.api path=/api/summary status=503 '
                       'error=LLMError detail="LLM 호출에 실패하였다: RateLimitError"')
    assert rec["time"] == "14:03:47"
    assert rec["level"] == "ERROR"
    assert rec["fields"]["status"] == "503"
    assert rec["fields"]["detail"] == "LLM 호출에 실패하였다: RateLimitError"


def test_형식이_다른_줄은_건너뛴다():
    s = load("log_summary")
    assert s.parse_line("이 줄은 기록이 아니다") is None


def test_한도_초과가_있던_날을_한_묶음으로_요약한다():
    s = load("log_summary")
    r = s.summarize(LOGS, "2027-09-08")
    assert r["requests"] == 82
    assert r["classes"]["5xx"] == 7
    assert len(r["error_groups"]) == 1
    g = r["error_groups"][0]
    assert (g["start"], g["end"], g["count"]) == ("14:03:47", "14:33:42", 7)
    assert r["llm_fail"] == {"RateLimitError": 7}
    assert r["candidates"] == 1


def test_느린_요청이_몰린_날은_지연_묶음이_장애_후보가_된다():
    s = load("log_summary")
    r = s.summarize(LOGS, "2027-09-10")
    assert r["error_groups"] == []
    slow = [g for g in r["slow_groups"] if g["path"] == "/api/ask"]
    assert slow and slow[0]["count"] == 11 and slow[0]["max_ms"] == 9364
    assert r["candidates"] == 1


def test_두_건짜리_오류는_장애_후보가_아니다():
    s = load("log_summary")
    r = s.summarize(LOGS, "2027-09-09")
    assert r["error_groups"][0]["count"] == 2
    assert r["candidates"] == 0


def test_간격이_30분을_넘으면_묶음을_나눈다(tmp_path):
    s = load("log_summary")
    lines = [
        "2027-09-20 10:00:00 ERROR jobprep.api path=/api/ask status=503 error=LLMError",
        "2027-09-20 10:10:00 ERROR jobprep.api path=/api/ask status=503 error=LLMError",
        "2027-09-20 11:00:00 ERROR jobprep.api path=/api/ask status=503 error=LLMError",
    ]
    (tmp_path / "error.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    r = s.summarize(tmp_path, "2027-09-20")
    assert [g["count"] for g in r["error_groups"]] == [2, 1]


def test_기록이_없는_날은_0건으로_요약한다():
    s = load("log_summary")
    out = s.render(s.summarize(LOGS, "2027-09-05"))
    assert "요청: 0건" in out


@pytest.mark.parametrize("argv", [["--date", "2027-9-8"], ["--date", "2027-09-08", "--logs", "없는폴더"]])
def test_잘못된_입력은_종료_코드_2(argv):
    s = load("log_summary")
    assert s.main(argv) == 2


# ---------- check_report.py ----------

GOOD = """# 장애 보고서: 2027-09-08 요약 기능 한도 초과로 연속 실패

- 심각도: SEV2 (LLM 기능 하나가 30분 안에 5xx 3건 이상)
- 작성: incident-report 스킬 초안, 검토자 홍길동
- 상태: 초안

## 1. 요약

요약 기능이 503을 냈다.

## 2. 영향

| 항목 | 값 |
|---|---|
| 영향받은 기능 | /api/summary |

## 3. 경과

| 시각 | 사건 | 근거 |
|---|---|---|
| 14:03:47 | 첫 503 | logs/error.log |
| 14:33:42 | 마지막 503 | logs/error.log |

## 4. 원인

RateLimitError (logs/llm.log). 한도를 넘긴 까닭은 확인 필요.

## 5. 조치와 재발 방지

- 기록에 조치 기록 없음

## 6. 근거 기록

- logs/error.log에서 2027-09-08 status=503
"""


def test_서식을_지킨_보고서는_통과한다():
    c = load("check_report")
    assert c.check(GOOD) == []


def test_절이_빠지면_위반이다():
    c = load("check_report")
    problems = c.check(GOOD.replace("## 5. 조치와 재발 방지", "## 5. 조치"))
    assert any("5. 조치와 재발 방지" in p for p in problems)


def test_경과_표에_근거가_없으면_위반이다():
    c = load("check_report")
    problems = c.check(GOOD.replace("| 14:33:42 | 마지막 503 | logs/error.log |", "| 14:33:42 | 마지막 503 | 기록 |"))
    assert any("2행" in p for p in problems)


def test_자리_표시가_남으면_위반이다():
    c = load("check_report")
    problems = c.check(GOOD.replace("검토자 홍길동", "검토자 {{이름}}"))
    assert any("자리 표시" in p for p in problems)


def test_심각도_줄이_없으면_위반이다():
    c = load("check_report")
    assert c.check(GOOD.replace("- 심각도: SEV2", "- 심각도: 높음"))


# ---------- SKILL.md 형식 ----------

def skill_text():
    path = skill_dir() / "SKILL.md"
    assert path.exists(), f"{path}가 없다"
    return path.read_text(encoding="utf-8")


def frontmatter(text):
    lines = text.splitlines()
    assert lines[0].strip() == "---", "첫 줄이 --- 이어야 한다"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    return "\n".join(lines[1:end])


def test_머리말에_폴더와_같은_name과_무엇과_언제가_있는_description이_있다():
    head = frontmatter(skill_text())
    assert re.search(r"^name:\s*incident-report\s*$", head, re.M), "name이 폴더 이름과 다르다"
    m = re.search(r"^description:\s*(.+)$", head, re.M)
    assert m and len(m.group(1)) >= 50, "description이 없거나 너무 짧다"
    assert "보고서" in m.group(1) and "사용" in m.group(1), "description에 무엇(보고서)과 언제(사용)가 함께 있어야 한다"


def test_본문은_60줄을_넘지_않는다():
    n = len(skill_text().splitlines())
    assert n <= 60, f"{n}줄이다(안티패턴 ① 거대 본문)"


def test_규칙에_이유가_붙어_있다():
    assert skill_text().count("왜냐하면") >= 2, "안티패턴 ③ 이유 없는 규칙"


def test_참조_파일과_스크립트를_본문에서_가리킨다():
    text = skill_text()
    for ref in ["references/보고서서식.md", "references/심각도기준.md",
                "scripts/log_summary.py", "scripts/check_report.py"]:
        assert ref in text, f"본문이 {ref}를 가리키지 않는다(가리키지 않은 파일은 읽히지 않는다)"
        assert (skill_dir() / ref).exists(), f"{ref} 파일이 없다"
