# -*- coding: utf-8 -*-
"""stdio MCP 서버를 띄워 도구·리소스·프롬프트의 목록과 설명을 그대로 보여 준다(5장).

모델은 도구의 설명과 인자 설명을 읽고 도구를 고른다. 이 스크립트는 모델이 읽을 글을
사람이 먼저 읽게 한다. 남이 만든 서버를 Claude Code에 연결하기 전에 쓴다.
도구를 호출하지는 않는다. 다만 서버를 실행하므로 서버의 코드는 실행된다(10절 참고).

사용법 (저장소 폴더에서, 가상 환경을 켠 뒤. -- 뒤의 python도 켠 가상 환경의 것이다)
    python ~/kits/Agent_05장/도구/show_tools.py -- python mcp/ops_server.py
    python ~/kits/Agent_05장/도구/show_tools.py --call error_summary '{"start": "2027-09-08"}' -- python mcp/ops_server.py
"""
import argparse
import asyncio
import json
import sys

from mcp import Client, StdioServerParameters


def parse_args():
    if "--" not in sys.argv:
        print(__doc__)
        sys.exit(2)
    cut = sys.argv.index("--")
    parser = argparse.ArgumentParser(description="stdio MCP 서버의 목록과 설명을 보여 준다")
    parser.add_argument("--call", nargs=2, metavar=("도구", "인자JSON"), help="도구 하나를 실제로 부른다")
    options = parser.parse_args(sys.argv[1:cut])
    command = sys.argv[cut + 1:]
    if not command:
        parser.error("-- 뒤에 서버를 띄우는 명령을 쓴다")
    return options, command


async def main():
    options, command = parse_args()
    params = StdioServerParameters(command=command[0], args=command[1:])
    async with Client(params) as client:
        tools = (await client.list_tools()).tools
        print(f"도구 {len(tools)}개")
        for t in tools:
            ann = t.annotations
            hints = "주석 없음" if ann is None else (
                f"readOnly={ann.read_only_hint} destructive={ann.destructive_hint} "
                f"idempotent={ann.idempotent_hint} openWorld={ann.open_world_hint}")
            print(f"\n== {t.name}  ({hints})")
            print(f"설명({len(t.description or '')}자):")
            for line in (t.description or "(없음)").splitlines():
                print(f"  | {line}")
            for arg, schema in t.input_schema.get("properties", {}).items():
                need = "필수" if arg in t.input_schema.get("required", []) else "선택"
                kind = schema.get("type") or " | ".join(s.get("type", "?") for s in schema.get("anyOf", []))
                extra = {k: schema[k] for k in ("enum", "minimum", "maximum", "default") if k in schema}
                print(f"  - {arg} [{kind}, {need}] {schema.get('description', '(인자 설명 없음)')} {extra or ''}")
        try:
            resources = (await client.list_resources()).resources
            print(f"\n리소스 {len(resources)}개: " + ", ".join(str(r.uri) for r in resources))
        except Exception as e:  # 리소스를 내놓지 않는 서버
            print(f"\n리소스: 없음 ({type(e).__name__})")
        try:
            prompts = (await client.list_prompts()).prompts
            print(f"프롬프트 {len(prompts)}개: " + ", ".join(p.name for p in prompts))
        except Exception as e:
            print(f"프롬프트: 없음 ({type(e).__name__})")
        if options.call:
            name, raw = options.call
            result = await client.call_tool(name, json.loads(raw))
            print(f"\n== 호출 {name} → isError={result.is_error}")
            for c in result.content:
                if c.type == "text":
                    print(c.text)


if __name__ == "__main__":
    asyncio.run(main())
