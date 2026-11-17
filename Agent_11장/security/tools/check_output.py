"""에이전트나 LLM이 낸 글을 밖으로 내보내기 전에 검사하는 출력 검사기이다. 11장 실습용.

이슈 댓글, 풀 리퀘스트 본문, 웹 화면, 저장소에 커밋할 파일처럼 「사람이나 다른 시스템이 받는 곳」으로
글이 나가기 전에 돌린다. 다음 네 가지를 본다.

1. secret: 비밀 정보의 모양(secret_patterns.py)
2. exfil_link: 바깥 주소로 가는 마크다운 그림·링크 가운데 질의 문자열(?…)이 있는 것.
   그림은 화면에 보이는 순간 브라우저가 주소를 불러오므로, 주소에 실린 데이터가 저절로 나간다.
3. active_html: 화면에 넣으면 실행될 수 있는 HTML(<script>, on…= 속성, javascript: 주소, <iframe>)
4. invisible: 보이지 않는 유니코드(폭 없는 문자, 태그 문자, 이형 선택자). 사람 눈에 안 보이는 지시나 데이터를 숨긴다.

종료 코드: 하나라도 찾으면 1, 없으면 0. --redact를 주면 비밀과 보이지 않는 문자를 지운 글을 표준 출력에 낸다.

쓰는 법
    python security/tools/check_output.py 파일
    에이전트_출력 | python security/tools/check_output.py -
    python security/tools/check_output.py 파일 --redact > 정리된_파일
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secret_patterns import PATTERNS, find_secrets  # noqa: E402

# 링크를 허용하는 주소. 이 목록 밖의 주소에 질의 문자열이 붙으면 유출 통로로 본다.
ALLOWED_HOSTS = {"github.com", "docs.github.com", "code.claude.com", "platform.claude.com",
                 "docs.python.org", "127.0.0.1", "localhost"}
MD_LINK = re.compile(r"(?P<image>!?)\[[^\]]*\]\((?P<url>[^)\s]+)[^)]*\)")
BARE_URL = re.compile(r"https?://[^\s)>\"']+")
ACTIVE_HTML = re.compile(r"(?i)<\s*script\b|<\s*iframe\b|\bon[a-z]+\s*=\s*['\"]|javascript\s*:")
INVISIBLE = re.compile("[​‌‍⁠﻿︀-️\U000e0000-\U000e007f]")


def host_allowed(url):
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_HOSTS or any(host.endswith("." + h) for h in ALLOWED_HOSTS)


def check(text):
    """찾은 문제를 (종류, 줄 번호, 설명) 목록으로 돌려준다."""
    problems = [("secret", lineno, f"{kind} {shown}") for lineno, kind, shown in find_secrets(text)]
    for lineno, line in enumerate(text.splitlines(), start=1):
        seen = set()
        for m in MD_LINK.finditer(line):
            url = m.group("url")
            seen.add(url)
            if url.startswith(("http://", "https://")) and not host_allowed(url):
                if m.group("image") or urlparse(url).query:
                    what = "그림" if m.group("image") else "링크"
                    problems.append(("exfil_link", lineno, f"바깥 주소로 가는 {what}: {urlparse(url).hostname}"))
        for m in BARE_URL.finditer(line):
            url = m.group(0)
            if url not in seen and urlparse(url).query and not host_allowed(url):
                problems.append(("exfil_link", lineno, f"질의 문자열이 붙은 바깥 주소: {urlparse(url).hostname}"))
        if ACTIVE_HTML.search(line):
            problems.append(("active_html", lineno, "실행될 수 있는 HTML"))
        hidden = INVISIBLE.findall(line)
        if hidden:
            codes = ", ".join(sorted({f"U+{ord(c):04X}" for c in hidden}))
            problems.append(("invisible", lineno, f"보이지 않는 문자 {len(hidden)}개 ({codes})"))
    return problems


def redact(text):
    for _, regex, _ in PATTERNS:
        text = regex.sub("[가림]", text)
    return INVISIBLE.sub("", text)


def main(argv=None):
    parser = argparse.ArgumentParser(description="내보낼 글의 출력 검사(학습용)")
    parser.add_argument("source", help="검사할 파일. -이면 표준 입력")
    parser.add_argument("--redact", action="store_true", help="비밀과 보이지 않는 문자를 지운 글을 출력한다")
    args = parser.parse_args(argv)
    if args.source == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.source).read_text(encoding="utf-8")
    problems = check(text)
    if args.redact:
        sys.stdout.write(redact(text))
    for kind, lineno, detail in problems:
        print(f"출력 검사: {kind} {lineno}번 줄: {detail}", file=sys.stderr)
    if problems:
        print(f"출력 검사: 문제 {len(problems)}건. 이 글을 그대로 내보내지 않는다.", file=sys.stderr)
        return 1
    print("출력 검사: 통과", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
