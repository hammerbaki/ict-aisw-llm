"""요청 한 번의 구조를 본다. ch09 폴더에서 실행한다.

    LLM_FAKE=1 python tools/first_call.py eval/공고/P01.txt          모의 모드
    LLM_FAKE=0 python tools/first_call.py eval/공고/P01.txt --schema 실제 호출(키가 있을 때만)

보낸 요청 본문(키 제외)과 받은 결과(본문, 토큰, 멈춘 이유)를 차례로 찍는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api import llm  # noqa: E402
from api.prompts import load_prompt  # noqa: E402
from api.schema import SUMMARY_SCHEMA, parse_summary  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("posting", help="공고 파일 경로")
    p.add_argument("--version", default="v3")
    p.add_argument("--schema", action="store_true", help="구조화 출력으로 형식을 강제한다")
    a = p.parse_args()

    prompt = load_prompt(a.version)
    posting = Path(a.posting).read_text(encoding="utf-8")
    result = llm.complete(prompt.system, prompt.render(posting), max_tokens=1024,
                          json_schema=SUMMARY_SCHEMA if a.schema else None)

    shown = dict(result.request)
    shown["system"] = shown["system"][:60] + " …(줄임)"
    shown["messages"] = [{"role": "user", "content": shown["messages"][0]["content"][:60] + " …(줄임)"}]
    if "format" in shown.get("output_config", {}):
        shown["output_config"] = {**shown["output_config"], "format": {"type": "json_schema", "schema": "…(줄임)"}}
    print("① 보낸 요청 (키는 요청 본문이 아니라 헤더로 간다)")
    print(json.dumps(shown, ensure_ascii=False, indent=2))
    print("② 받은 본문")
    print(result.text)
    print(f"③ 사용량  input_tokens={result.input_tokens}  output_tokens={result.output_tokens}"
          f"  stop_reason={result.stop_reason}  모의={result.fake}")
    summary, reason = parse_summary(result.text)
    print("④ 형식 검사", "통과" if summary else f"실패 - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
