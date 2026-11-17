"""목록 화면의 관심 공고 내보내기 단추의 인수 테스트 (REQ-FAV-05). ISSUE-07 작업 T2.

웹 코드는 브라우저에서 돌므로 pytest로 실행하지 않는다. 이 테스트는 파일의 구조만 본다(정적 검사).
단추를 눌러 CSV가 내려받아지는지는 화면에서 확인한다(명세서의 상태: 구현(수동)).
"""

from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


def test_export_script_exists_and_uses_contract():
    script = (WEB / "js" / "export.js").read_text(encoding="utf-8")
    assert "/api/favorites/export" in script      # 계획서의 계약: 경로
    assert "ids" in script                        # 계획서의 계약: 질의 매개변수
    assert "loadFavorites()" in script            # 관심 공고는 common.js의 함수로 읽는다


def test_export_script_does_not_insert_html():
    script = (WEB / "js" / "export.js").read_text(encoding="utf-8")
    for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert banned not in script


def test_list_page_has_export_button():
    page = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="export-favorites"' in page


def test_export_script_loads_after_common_and_list():
    page = (WEB / "index.html").read_text(encoding="utf-8")
    common = page.find('src="js/common.js"')
    listing = page.find('src="js/list.js"')
    export = page.find('src="js/export.js"')
    assert -1 < common < listing < export
