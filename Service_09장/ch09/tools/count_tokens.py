"""프롬프트 판본별 입력 토큰을 센다. ch09 폴더에서 실행한다.

    LLM_FAKE=0 python tools/count_tokens.py eval/공고/P01.txt v1 v2 v3   실제 count_tokens API(무료, 별도 한도)
    LLM_FAKE=1 python tools/count_tokens.py eval/공고/P01.txt v1 v2 v3   모의 어림값(글자 수 × 0.8, 실제와 다르다)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api import llm  # noqa: E402
from api.prompts import load_prompt  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    posting = Path(sys.argv[1]).read_text(encoding="utf-8")
    for version in sys.argv[2:]:
        prompt = load_prompt(version)
        n, fake = llm.count_tokens(prompt.system, prompt.render(posting))
        print(f"{version}: 입력 {n} 토큰" + ("  (모의 어림값)" if fake else f"  (모델 {llm.model_name()})"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
