"""키보드 이동 기록기 (선택 도구, Playwright 필요).

브라우저에서 HTML 파일을 열고 Tab 키를 정해진 횟수만큼 눌러, 초점이 어느 요소로 어떤 순서로
옮겨 가는지와 초점 표시가 보이는지를 표로 남긴다. 사람이 하는 키보드 점검을 대신하지 않는다.
사람이 점검한 순서와 이 기록을 대조하는 데 쓴다.

준비 (한 번만)
    가상 환경을 켠 터미널에서 python -m pip install -r requirements.txt   (playwright==1.64.0)
    Windows에 Edge나 Chrome이 있으면 브라우저를 받지 않고 --channel msedge 또는 --channel chrome
    둘 다 없으면 python -m playwright install --only-shell chromium      (부록 A-18)

사용법
    python tools/keyboard_walk.py prototype/index.html
    python tools/keyboard_walk.py prototype/index.html --tabs 20 --channel msedge
    python tools/keyboard_walk.py prototype/index.html --enter "단축키"

출력의 「초점 표시」 칸은 초점을 받은 요소의 계산된 outline 또는 box-shadow가 있는지만 본다.
표시의 대비(3:1)와 크기는 눈으로 확인한다.
"""
import argparse
import sys
from pathlib import Path

PROBE = """
() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const cs = getComputedStyle(el);
  const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
  const shadow = cs.boxShadow && cs.boxShadow !== 'none';
  let name = el.getAttribute('aria-label') || '';
  if (!name && el.labels && el.labels.length) name = el.labels[0].innerText;
  if (!name) name = (el.innerText || el.value || el.getAttribute('alt') || '').trim();
  const r = el.getBoundingClientRect();
  return {tag: el.tagName.toLowerCase(), id: el.id, name: name.replace(/\\s+/g, ' ').slice(0, 30),
          visible: outline || shadow, w: Math.round(r.width), h: Math.round(r.height)};
}
"""


def walk(page, tabs):
    rows = []
    for i in range(1, tabs + 1):
        page.keyboard.press("Tab")
        info = page.evaluate(PROBE)
        rows.append((i, info))
    return rows


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="Tab 키로 초점 순서를 기록한다")
    ap.add_argument("file")
    ap.add_argument("--tabs", type=int, default=12)
    ap.add_argument("--channel", help="msedge 또는 chrome (설치된 브라우저를 쓴다)")
    ap.add_argument("--enter", help="이 이름의 요소에 초점이 오면 Enter를 누르고 결과 화면을 보인다")
    args = ap.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright가 없다. pip install playwright==1.64.0 을 먼저 한다.")
        return 2

    url = Path(args.file).resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel) if args.channel else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url)
        print(f"페이지: {page.title()}  ({args.file})")
        print(f"{'순서':>2}  {'요소':<8}{'이름':<30}{'초점표시':<4}{'크기(px)':>8}")
        seen, problems = [], 0
        for i, info in walk(page, args.tabs):
            if info is None:
                print(f"{i:>4}  (초점이 문서 밖 또는 body로 나감. 한 바퀴를 돌았다)")
                break
            key = (info["tag"], info["id"], info["name"])
            mark = "있음" if info["visible"] else "없음"
            small = info["w"] < 24 or info["h"] < 24
            note = "  작음(24px 미만)" if small else ""
            print(f"{i:>4}  {info['tag']:<10}{info['name']:<32}{mark:<6}{info['w']:>4}x{info['h']:<4}{note}")
            problems += (not info["visible"]) + small
            if args.enter and info["name"] == args.enter:
                page.keyboard.press("Enter")
                page.wait_for_timeout(300)
                print(f"      Enter -> {page.title()}  {page.url.rsplit('/', 1)[-1]}")
                break
            if seen.count(key) >= 2:
                print("      같은 요소에 세 번 머물렀다. 키보드 함정(2.1.2)인지 확인한다")
                problems += 1
                break
            seen.append(key)
        browser.close()
    print(f"\n주의할 항목 {problems}건 (초점 표시 없음, 24px 미만, 함정 의심)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
