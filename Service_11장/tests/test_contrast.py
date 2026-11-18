"""대비 계산기의 테스트. WCAG 2.2의 공식과 알려진 값으로 검사한다."""
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "tools"))

import contrast  # noqa: E402
from tokenfile import TokenError, parse, resolve  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


def test_black_on_white_is_21():
    assert contrast.ratio("#000000", "#ffffff") == pytest.approx(21.0)


def test_same_color_is_1():
    assert contrast.ratio("#1d4ed8", "#1d4ed8") == pytest.approx(1.0)


def test_order_does_not_matter():
    assert contrast.ratio("#ffffff", "#767676") == contrast.ratio("#767676", "#ffffff")


def test_short_hex():
    assert contrast.hex_to_rgb("#fff") == (255, 255, 255)
    assert contrast.ratio("#000", "#fff") == pytest.approx(21.0)


def test_luminance_threshold_branch():
    # 8비트 10은 10/255 = 0.0392 <= 0.04045 이므로 선형 구간(나누기 12.92)을 탄다
    assert contrast.channel(10) == pytest.approx((10 / 255) / 12.92)
    assert contrast.channel(11) == pytest.approx(((11 / 255 + 0.055) / 1.055) ** 2.4)


def test_known_boundary_grays():
    # #767676은 흰 바탕에서 4.5를 넘는 가장 밝은 회색으로 알려져 있다. #777777은 넘지 못한다
    assert contrast.floor2(contrast.ratio("#767676", "#ffffff")) == 4.54
    assert contrast.floor2(contrast.ratio("#777777", "#ffffff")) == 4.47


def test_floor_not_round():
    assert contrast.floor2(4.4999) == 4.49


def test_bad_hex():
    with pytest.raises(ValueError):
        contrast.hex_to_rgb("blue")


def test_alias_resolution():
    tokens, _ = parse("| `a` | `#000000` | |\n| `b` | `{a}` | |\n| `c` | `{b}` | |\n")
    assert resolve("c", tokens) == "#000000"


def test_alias_cycle_and_missing():
    tokens, _ = parse("| `a` | `{b}` | |\n| `b` | `{a}` | |\n| `c` | `{zzz}` | |\n")
    with pytest.raises(TokenError, match="순환"):
        resolve("a", tokens)
    with pytest.raises(TokenError, match="없는 토큰"):
        resolve("c", tokens)


def test_sample_tokens_find_one_failure(capsys):
    code = contrast.main([str(FIX / "tokens_sample.md")])
    out = capsys.readouterr().out
    assert code == 1
    assert "미달 1건" in out
    assert "color-text-muted" in out


def test_fromscratch_colors():
    # FromScratch v1.4.3의 본문 글자(#829696)와 바탕(#002b36), 저장 안내의 합성색
    assert contrast.floor2(contrast.ratio("#829696", "#002b36")) == 4.82
    assert contrast.floor2(contrast.ratio("#758d92", "#1a404a")) == 3.18


def test_pair_cli(capsys):
    assert contrast.main(["--pair", "#767676", "#ffffff"]) == 0
    assert contrast.main(["--pair", "#777777", "#ffffff"]) == 1
    assert contrast.main(["--pair", "#949494", "#ffffff", "--min", "3"]) == 0
    assert "통과" in capsys.readouterr().out


def test_kit_sample_has_known_failure():
    # 키트의 견본은 원본 앱(FromScratch)의 저장 안내 색을 옮겨 미달 한 쌍(3.18:1)을 둔다
    code = contrast.main([str(KIT / "디자인토큰_견본.md")])
    assert code == 1


def test_teacher_answer_passes():
    answer = KIT / "교수" / "정답" / "디자인토큰.md"
    if not answer.exists():
        pytest.skip("교수 폴더가 없는 배포본")
    assert contrast.main([str(answer)]) == 0
