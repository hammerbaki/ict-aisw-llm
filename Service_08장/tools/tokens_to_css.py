"""디자인토큰.md를 CSS 사용자 지정 속성 파일(tokens.css)로 바꾼다.

사용법
    python tools/tokens_to_css.py 디자인토큰.md                 화면에 출력
    python tools/tokens_to_css.py 디자인토큰.md -o prototype/css/tokens.css

토큰의 원본은 디자인토큰.md 하나다. tokens.css는 이 도구가 만드는 결과물이므로 손으로 고치지 않는다.
값을 바꾸려면 디자인토큰.md를 고치고 이 도구를 다시 실행한다.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tokenfile import TokenError, load, resolve, to_css_value  # noqa: E402

HEADER = ("/* 이 파일은 tools/tokens_to_css.py가 {src}에서 만든다. 직접 고치지 않는다.\n"
          "   값을 바꾸려면 {src}를 고치고 도구를 다시 실행한다. */\n")


def build(tokens, src_name="디자인토큰.md"):
    for name in tokens:  # 없는 토큰을 가리키거나 순환하는 별칭은 여기서 걸린다
        resolve(name, tokens)
    out = [HEADER.format(src=src_name), ":root {"]
    group = None
    for name, t in tokens.items():
        if t["group"] != group:
            group = t["group"]
            if len(out) > 2:
                out.append("")
            out.append(f"  /* {group} */")
        out.append(f"  --{name}: {to_css_value(t['value'])};")
    out.append("}")
    return "\n".join(out) + "\n"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="디자인토큰.md -> tokens.css")
    ap.add_argument("file")
    ap.add_argument("-o", "--output")
    args = ap.parse_args(argv)
    try:
        tokens, _ = load(args.file)
        css = build(tokens, Path(args.file).name)
    except (TokenError, OSError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(css, encoding="utf-8", newline="\n")
        print(f"토큰 {len(tokens)}개 -> {args.output}")
    else:
        sys.stdout.write(css)
    return 0


if __name__ == "__main__":
    sys.exit(main())
