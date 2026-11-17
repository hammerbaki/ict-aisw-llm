"""색 대비 계산기: WCAG 2.2의 상대 휘도와 대비율 공식으로 색 쌍을 판정한다.

사용법
    python tools/contrast.py 디자인토큰.md              「대비 쌍」 표의 모든 쌍을 판정한다
    python tools/contrast.py --pair "#767676" "#ffffff"  두 색을 바로 잰다(기준 4.5)
    python tools/contrast.py --pair "#767676" "#ffffff" --min 3

종료 코드: 모든 쌍이 기준 이상이면 0, 하나라도 미달이면 1, 파일 형식 오류는 2.

공식 (WCAG 2.2, 용어 정의 「relative luminance」, 「contrast ratio」)
    채널 c = 8비트 값 / 255
    c <= 0.04045 이면 c / 12.92, 아니면 ((c + 0.055) / 1.055) ** 2.4
    L = 0.2126 R + 0.7152 G + 0.0722 B
    대비율 = (밝은 쪽 L + 0.05) / (어두운 쪽 L + 0.05)     범위 1 ~ 21
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tokenfile import HEX, TokenError, load, resolve  # noqa: E402


def hex_to_rgb(value):
    """'#1d4ed8' 또는 '#fff'를 (29, 78, 216)으로 바꾼다."""
    if not HEX.match(value):
        raise ValueError(f"16진 색이 아니다: {value!r} (#rrggbb 또는 #rgb)")
    h = value[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def channel(c8):
    c = c8 / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(value):
    r, g, b = (channel(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    la, lb = luminance(fg), luminance(bg)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def floor2(x):
    """판정에 쓰는 값은 반올림하지 않고 소수 둘째 자리에서 버린다.

    4.499를 반올림하면 4.50이 되어 통과처럼 보인다. WCAG는 기준값의 반올림을 허용하지 않으므로 버린다.
    """
    return math.floor(x * 100) / 100


def check_pairs(tokens, pairs):
    """대비 쌍마다 (쌍, 전경 색, 배경 색, 대비율, 통과 여부)를 돌려준다."""
    rows = []
    for p in pairs:
        fg = p["fg"] if HEX.match(p["fg"]) else resolve(p["fg"], tokens)
        bg = p["bg"] if HEX.match(p["bg"]) else resolve(p["bg"], tokens)
        r = ratio(fg, bg)
        rows.append((p, fg, bg, r, floor2(r) >= p["min"]))
    return rows


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="WCAG 2.2 대비율 계산")
    ap.add_argument("file", nargs="?", help="디자인토큰.md")
    ap.add_argument("--pair", nargs=2, metavar=("FG", "BG"), help="두 색을 바로 잰다")
    ap.add_argument("--min", type=float, default=4.5, help="--pair의 기준(기본 4.5)")
    args = ap.parse_args(argv)

    if args.pair:
        fg, bg = args.pair
        try:
            r = ratio(fg, bg)
        except ValueError as exc:
            print(f"오류: {exc}", file=sys.stderr)
            return 2
        ok = floor2(r) >= args.min
        print(f"{fg} / {bg}  대비 {floor2(r):.2f}:1  기준 {args.min:g}  {'통과' if ok else '미달'}")
        print(f"  상대 휘도  {fg}: {luminance(fg):.4f}   {bg}: {luminance(bg):.4f}")
        return 0 if ok else 1

    if not args.file:
        ap.print_help()
        return 2
    try:
        tokens, pairs = load(args.file)
        rows = check_pairs(tokens, pairs)
    except (TokenError, ValueError, OSError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    if not pairs:
        print("오류: 「대비 쌍」 절에 쌍이 하나도 없다", file=sys.stderr)
        return 2

    colors = sum(1 for t in tokens.values() if HEX.match(t["value"]) or t["value"].startswith("{"))
    print(f"대비 점검: {args.file}  (토큰 {len(tokens)}개 중 색 {colors}개, 쌍 {len(pairs)}개)")
    print(f"{'전경':<20}{'배경':<20}{'대비':>6}  {'기준':>2}  판정  용도")
    failed = 0
    for p, fg, bg, r, ok in rows:
        failed += not ok
        mark = "통과" if ok else "미달"
        print(f"{p['fg']:<22}{p['bg']:<22}{floor2(r):>6.2f}:1  {p['min']:>4g}  {mark}  {p['use']}")
    print()
    if failed:
        print(f"미달 {failed}건. 미달한 쌍의 줄 번호: "
              + ", ".join(str(p['line']) for p, *_, ok in rows if not ok))
        return 1
    print("모든 쌍이 기준 이상이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
