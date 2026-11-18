"""HTML 기본 접근성 점검기 (표준 라이브러리의 html.parser만 쓴다).

사용법
    python tools/html_check.py prototype/              폴더 안의 모든 .html
    python tools/html_check.py prototype/index.html    파일 하나

점검하는 것 (괄호는 관련 WCAG 2.2 성공 기준)
    오류  html-lang     <html>에 lang 속성이 없거나 비었다                     (3.1.1)
    오류  title         <title>이 없거나 비었다                                (2.4.2)
    오류  img-alt       <img>에 alt 속성이 없다. 장식 이미지는 alt=""로 둔다    (1.1.1)
    오류  form-label    입력 요소에 연결된 레이블이 없다                       (1.3.1, 3.3.2, 4.1.2)
    오류  button-name   <button>에 읽을 수 있는 이름이 없다                    (4.1.2)
    오류  link-name     <a href>에 읽을 수 있는 이름이 없다                    (2.4.4, 4.1.2)
    오류  duplicate-id  같은 id가 두 번 이상 쓰였다(레이블 연결이 깨진다)
    경고  tabindex      tabindex가 0보다 크다(초점 순서가 문서 순서와 어긋난다) (2.4.3)
    경고  div-click     div나 span에 onclick이 있다(키보드로 누를 수 없다)       (2.1.1)

이 점검기가 판정하지 못하는 것: 대체 텍스트의 적절성, 레이블 문구의 명확성, 초점 표시의 대비,
실제 키보드 이동 순서, 화면 낭독기의 읽기 결과. 이것들은 사람이 확인한다.

종료 코드: 오류가 없으면 0, 오류가 있으면 1. 경고만 있으면 0.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path

LABELABLE_SKIP = {"hidden", "submit", "button", "reset", "image"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr"}


class Finding:
    def __init__(self, path, line, level, rule, message):
        self.path, self.line, self.level, self.rule, self.message = path, line, level, rule, message

    def __str__(self):
        return f"{self.path}:{self.line}  {self.level}  {self.rule:<13}{self.message}"


class Checker(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.findings = []
        self.html_lang = None
        self.saw_html = False
        self.title_text = None
        self.in_title = False
        self.ids = {}
        self.label_for = set()
        self.label_depth = 0
        self.controls = []        # (line, id, has_aria_name, inside_label, desc)
        self.named_stack = []     # 열린 button / a 의 [tag, line, text, has_aria, img_alt]

    # 결과 기록
    def add(self, line, level, rule, message):
        self.findings.append(Finding(self.path, line, level, rule, message))

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        line = self.getpos()[0]

        if "id" in a and a["id"]:
            self.ids.setdefault(a["id"], []).append(line)
        if "tabindex" in a:
            try:
                if int(a["tabindex"]) > 0:
                    self.add(line, "경고", "tabindex",
                             f"tabindex=\"{a['tabindex']}\". 0 또는 -1만 쓰고 순서는 문서 순서로 정한다")
            except ValueError:
                pass
        if tag in ("div", "span") and "onclick" in a:
            self.add(line, "경고", "div-click", f"<{tag} onclick>은 키보드로 누를 수 없다. <button>을 쓴다")

        has_aria = bool(a.get("aria-label", "").strip() or a.get("aria-labelledby", "").strip())

        if tag == "html":
            self.saw_html = True
            self.html_lang = a.get("lang", "").strip()
        elif tag == "title":
            self.in_title = True
            self.title_text = ""
        elif tag == "label":
            self.label_depth += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        elif tag == "img":
            if "alt" not in a:
                src = a.get("src", "")
                self.add(line, "오류", "img-alt",
                         f"<img src=\"{src}\">에 alt가 없다. 의미 있으면 설명을, 장식이면 alt=\"\"를 쓴다")
            for item in self.named_stack:
                if a.get("alt", "").strip():
                    item[4] = True
        elif tag in ("input", "select", "textarea"):
            kind = a.get("type", "text").lower() if tag == "input" else tag
            if tag == "input" and kind == "image" and not a.get("alt", "").strip():
                self.add(line, "오류", "img-alt", "<input type=\"image\">에 alt가 없다")
            if kind not in LABELABLE_SKIP:
                desc = f"<{tag} type=\"{kind}\">" if tag == "input" else f"<{tag}>"
                if a.get("name"):
                    desc += f" name=\"{a['name']}\""
                self.controls.append((line, a.get("id", ""), has_aria, self.label_depth > 0, desc))
        if tag in ("button", "a"):
            if tag == "a" and "href" not in a:
                pass  # 이름 없는 앵커(목적지)는 링크가 아니다
            else:
                self.named_stack.append([tag, line, "", has_aria, False])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "label":
            self.label_depth = max(0, self.label_depth - 1)
        elif tag in ("button", "a"):
            for i in range(len(self.named_stack) - 1, -1, -1):
                if self.named_stack[i][0] == tag:
                    _, line, text, has_aria, img_alt = self.named_stack.pop(i)
                    if not (text.strip() or has_aria or img_alt):
                        rule = "button-name" if tag == "button" else "link-name"
                        what = "<button>" if tag == "button" else "<a href>"
                        self.add(line, "오류", rule,
                                 f"{what}에 글자도 aria-label도 없다. 화면 낭독기가 이름을 읽지 못한다")
                    break

    def handle_data(self, data):
        if self.in_title:
            self.title_text += data
        for item in self.named_stack:
            item[2] += data

    def finish(self):
        if not self.saw_html or not self.html_lang:
            self.add(1, "오류", "html-lang", "<html lang=\"ko\">처럼 문서의 언어를 밝힌다")
        if not (self.title_text or "").strip():
            self.add(1, "오류", "title", "<title>에 화면 이름을 쓴다")
        for line, cid, has_aria, inside_label, desc in self.controls:
            if not (has_aria or inside_label or (cid and cid in self.label_for)):
                hint = f"<label for=\"{cid}\">" if cid else "id와 <label for>"
                self.add(line, "오류", "form-label", f"{desc}에 레이블이 없다. {hint}로 연결한다")
        for ident, lines in self.ids.items():
            if len(lines) > 1:
                self.add(lines[1], "오류", "duplicate-id",
                         f"id=\"{ident}\"가 {', '.join(map(str, lines))}줄에 거듭 있다")
        self.findings.sort(key=lambda f: f.line)
        return self.findings


def check_file(path):
    checker = Checker(str(path))
    checker.feed(Path(path).read_text(encoding="utf-8"))
    checker.close()
    return checker.finish()


def collect(targets):
    files = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.html")))
        elif p.exists():
            files.append(p)
        else:
            raise FileNotFoundError(f"없는 경로: {t}")
    return files


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    try:
        files = collect(argv)
    except FileNotFoundError as exc:
        print(f"오류: {exc}")
        return 2
    errors = warnings = 0
    for f in files:
        for finding in check_file(f):
            print(finding)
            errors += finding.level == "오류"
            warnings += finding.level == "경고"
    print(f"\n파일 {len(files)}개, 오류 {errors}건, 경고 {warnings}건")
    if not errors:
        print("기본 점검 통과. 대체 텍스트의 적절성, 초점 표시, 키보드 순서는 사람이 확인한다.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
