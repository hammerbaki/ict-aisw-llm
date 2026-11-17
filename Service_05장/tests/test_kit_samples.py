"""키트에 든 예시 기록과 견본이 서로 맞는지 확인한다(키트를 고친 뒤 깨지지 않게)."""
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "tools"))
import check_pii  # noqa: E402
import check_trace  # noqa: E402

RECORDS = KIT / "예시기록"


def test_example_records_are_clean():
    assert check_pii.main([str(RECORDS)]) == 0


@pytest.mark.skipif(not (KIT / "교수").exists(), reason="학생 배포본에는 교수 폴더가 없다")
def test_teacher_samples_pass():
    targets = [str(KIT / "교수" / n) for n in ("견본_친화도.md", "견본_페르소나.md", "견본_문제정의.md")]
    assert check_trace.main(targets + ["--records", str(RECORDS)]) == 0


def test_flawed_persona_counts(capsys):
    code = check_trace.main([str(KIT / "연습" / "잘못된_페르소나.md"), "--records", str(RECORDS)])
    out = capsys.readouterr().out
    assert code == 1
    assert "결과: 불통과 (실패 2, 누락 1, 경고 2)" in out
