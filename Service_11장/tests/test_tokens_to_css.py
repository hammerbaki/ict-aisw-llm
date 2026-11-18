"""디자인토큰.md -> tokens.css 변환의 테스트."""
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "tools"))

import tokens_to_css  # noqa: E402
from tokenfile import TokenError, parse  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


def test_alias_becomes_var():
    tokens, _ = parse((FIX / "tokens_sample.md").read_text(encoding="utf-8"))
    css = tokens_to_css.build(tokens)
    assert "--color-text: var(--ink);" in css
    assert "--space-pad: var(--space-2);" in css
    assert "--white: #ffffff;" in css
    assert css.strip().startswith("/*") and css.strip().endswith("}")


def test_pairs_are_not_tokens():
    tokens, pairs = parse((FIX / "tokens_sample.md").read_text(encoding="utf-8"))
    assert len(pairs) == 4
    assert "color-text-muted" in tokens and "#949494" not in tokens


def test_group_comments():
    tokens, _ = parse((FIX / "tokens_sample.md").read_text(encoding="utf-8"))
    css = tokens_to_css.build(tokens)
    assert "/* 색 */" in css and "/* 간격 */" in css


def test_missing_alias_is_error():
    tokens, _ = parse("| `a` | `{nope}` | |\n")
    with pytest.raises(TokenError):
        tokens_to_css.build(tokens)


def test_bad_name_and_duplicate():
    with pytest.raises(TokenError, match="소문자"):
        parse("| `Color_Text` | `#000` | |\n")
    with pytest.raises(TokenError, match="줄에도"):
        parse("| `a` | `#000` | |\n| `a` | `#fff` | |\n")


def test_header_rows_ignored():
    tokens, _ = parse("| 토큰 | 값 | 설명 |\n|---|---|---|\n| `a` | `#000` | 검정 |\n")
    assert list(tokens) == ["a"]


def test_cli_writes_file(tmp_path):
    out = tmp_path / "tokens.css"
    assert tokens_to_css.main([str(KIT / "디자인토큰_견본.md"), "-o", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "--color-status-text: var(--gray-50);" in text
    assert "--space-3: 1rem;" in text
