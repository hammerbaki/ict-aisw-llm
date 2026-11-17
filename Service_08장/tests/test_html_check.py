"""HTML 기본 점검기의 테스트."""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "tools"))

import html_check  # noqa: E402


def rules_of(html, tmp_path):
    f = tmp_path / "t.html"
    f.write_text(html, encoding="utf-8")
    return [(x.level, x.rule) for x in html_check.check_file(f)]


GOOD_HEAD = '<!doctype html><html lang="ko"><head><title>화면</title></head><body>'


def test_missing_lang_and_title(tmp_path):
    rules = rules_of("<html><body><p>안녕</p></body></html>", tmp_path)
    assert ("오류", "html-lang") in rules
    assert ("오류", "title") in rules


def test_empty_lang_is_error(tmp_path):
    rules = rules_of('<html lang=""><head><title>t</title></head></html>', tmp_path)
    assert ("오류", "html-lang") in rules


def test_img_alt(tmp_path):
    rules = rules_of(GOOD_HEAD + '<img src="a.png"><img src="b.png" alt="">', tmp_path)
    assert rules.count(("오류", "img-alt")) == 1  # alt=""(장식)는 통과


def test_label_variants(tmp_path):
    html = GOOD_HEAD + """
      <label for="a">이름</label><input id="a">
      <label>전화 <input name="tel"></label>
      <input aria-label="검색">
      <input id="lonely" name="lonely">
      <input type="hidden" name="h"><input type="submit" value="보내기">
      <select id="s"></select><textarea></textarea>
    """
    rules = rules_of(html, tmp_path)
    assert rules.count(("오류", "form-label")) == 3  # lonely, select, textarea


def test_placeholder_is_not_label(tmp_path):
    rules = rules_of(GOOD_HEAD + '<input name="q" placeholder="검색어">', tmp_path)
    assert ("오류", "form-label") in rules


def test_button_names(tmp_path):
    html = GOOD_HEAD + """
      <button>저장</button>
      <button aria-label="닫기"><svg></svg></button>
      <button><img src="x.svg" alt="삭제"></button>
      <button><img src="x.svg"></button>
      <button>   </button>
    """
    rules = rules_of(html, tmp_path)
    assert rules.count(("오류", "button-name")) == 2


def test_link_names(tmp_path):
    html = GOOD_HEAD + '<a href="a.html">공고</a><a href="b.html"><img src="i.svg" alt=""></a><a id="top"></a>'
    rules = rules_of(html, tmp_path)
    assert rules.count(("오류", "link-name")) == 1


def test_warnings(tmp_path):
    html = GOOD_HEAD + '<div onclick="go()">이동</div><a href="#" tabindex="2">x</a><p tabindex="0">p</p>'
    rules = rules_of(html, tmp_path)
    assert ("경고", "div-click") in rules
    assert rules.count(("경고", "tabindex")) == 1


def test_duplicate_id(tmp_path):
    rules = rules_of(GOOD_HEAD + '<p id="m">a</p><p id="m">b</p>', tmp_path)
    assert ("오류", "duplicate-id") in rules


def test_bad_example_findings(capsys):
    code = html_check.main([str(KIT / "예제" / "일정등록_나쁜예.html")])
    out = capsys.readouterr().out
    assert code == 1
    for rule in ("html-lang", "img-alt", "form-label", "button-name", "link-name",
                 "duplicate-id", "tabindex", "div-click"):
        assert rule in out, rule


def test_teacher_prototype_passes():
    proto = KIT / "교수" / "정답" / "prototype"
    if not proto.exists():
        import pytest
        pytest.skip("교수 폴더가 없는 배포본")
    assert html_check.main([str(proto)]) == 0


def test_starter_prototype_passes():
    assert html_check.main([str(KIT / "prototype_시작")]) == 0
