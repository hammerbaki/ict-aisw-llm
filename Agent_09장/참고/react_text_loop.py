"""글 서식으로 도는 ReAct 루프(2026년 2학기판 LLM 8주차 react_agent.py의 완성본을 이 장에 맞게 고친 것).

API의 도구 사용(tool_use, tool_result)을 쓰지 않는다. 모델에게 "생각: / 행동: / 입력:" 서식으로만
답하게 하고, 그 글을 이 코드가 정규 표현 없이 줄 단위로 읽어 행동을 고른다. 9장 9절에서
API의 도구 사용과 무엇이 같고 무엇이 다른지 대조한다.

사용법
    python react_text_loop.py mock        # 모의 각본으로 루프만 확인(API 불필요)
"""

import sys

MAX_STEPS = 5

SYSTEM = """너는 도구를 쓰는 상담원이다. 반드시 아래 서식으로만 답한다.

생각: (다음에 무엇을 할지 한 문장)
행동: (vat_calc 또는 discount_calc 또는 finish 중 하나)
입력: (vat_calc는 공급가액 숫자, discount_calc는 "원가,할인율", finish는 최종 답)

규칙: 한 번에 행동 하나만 쓴다. 계산은 직접 하지 말고 반드시 도구로 한다."""


def vat_calc(raw):
    try:
        amount = float(str(raw).replace(",", "").replace("원", "").strip())
    except ValueError:
        return "오류: 숫자가 필요하다"
    if amount < 0:
        return "오류: 금액은 0 이상이어야 한다"
    vat = round(amount * 0.1)
    return f"공급가액 {amount:,.0f}원, 부가세 {vat:,}원, 합계 {amount + vat:,.0f}원"


def discount_calc(raw):
    try:
        price_s, rate_s = str(raw).split(",")
        price, rate = float(price_s), float(rate_s)
    except ValueError:
        return "오류: '원가,할인율' 형식이 필요하다 (예: 50000,20)"
    if not 0 <= rate <= 100:
        return "오류: 할인율은 0~100 사이여야 한다"
    return f"원가 {price:,.0f}원, {rate:g}% 할인 적용가 {round(price * (1 - rate / 100)):,}원"


TOOLS = {"vat_calc": vat_calc, "discount_calc": discount_calc}


def parse_action(text):
    """모델의 글에서 (행동, 입력)을 골라낸다. 행동 줄이 없으면 글 전체를 최종 답으로 본다."""
    action, arg = None, ""
    for line in text.splitlines():
        if line.startswith("행동:"):
            action = line[len("행동:"):].strip()
        elif line.startswith("입력:"):
            arg = line[len("입력:"):].strip()
    if action is None:
        return "finish", text
    return action, arg


def run_loop(llm, question):
    prompt = f"사용자 질문: {question}\n"
    for step in range(1, MAX_STEPS + 1):
        text = llm.generate(SYSTEM, prompt)
        print(f"\n[{step}단계 모델 출력]\n{text}")
        action, arg = parse_action(text)
        if action == "finish":
            return arg
        observation = TOOLS[action](arg) if action in TOOLS else f"오류: 알 수 없는 행동 {action}"
        print(f"[관찰] {observation}")
        prompt += text + f"\n관찰: {observation}\n"     # 관찰을 글 끝에 이어 붙인다
    return "중단: 최대 단계 수를 넘었다"


class MockLLM:
    def __init__(self, script):
        self.script = list(script)

    def generate(self, system, prompt):
        return self.script.pop(0)


MOCK_SCRIPT = [
    "생각: 부가세부터 계산한다\n행동: vat_calc\n입력: 1000000",
    "생각: 합계에 20% 할인을 적용한다\n행동: discount_calc\n입력: 1100000,20",
    "생각: 답을 정리한다\n행동: finish\n입력: 부가세 포함 110만 원에서 20% 할인하면 880,000원이다",
]

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows에서 파이프로 넘겨도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")
    if len(sys.argv) == 2 and sys.argv[1] == "mock":
        print(f"\n[최종 답] {run_loop(MockLLM(MOCK_SCRIPT), '100만 원 노트북, 부가세 포함가에서 20% 할인하면?')}")
    else:
        print(__doc__)
        sys.exit(1)
