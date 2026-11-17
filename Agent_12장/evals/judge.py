"""LLM 판정(LLM-as-a-judge)의 자리.

규칙 채점기가 보지 못하는 기준(근거에 없는 내용을 지어냈는가)을 판정한다.

- backend="real": judge_rubric.md의 기준표로 프롬프트를 만들어 llm.complete(task="judge")로 묻는다.
  API 키가 있어야 하며, 이 교재를 쓸 때는 실행하지 않았다(확인하지 못함).
- backend="sim": 모의 판정자. 출력의 문장마다 근거의 문장과 글자 bigram 유사도를 재어,
  가장 비슷한 근거 문장과의 유사도가 SUPPORT_MIN보다 낮은 문장이 있으면 fail로 본다.
  결정적으로 돌지만, 뜻은 같고 낱말이 다른 문장(표현 차이)을 fail로, 낱말은 같고 뜻이
  뒤집힌 문장(왜곡)을 pass로 잘못 판정하는 한계가 있다. 이 한계는 사람 표본과 대조해 드러난다.

명령행
    python -m evals.judge pairwise-demo    위치 편향을 일부러 넣은 모의 판정자로 순서 바꾸기 점검을 보인다
"""

import re
import sys
from pathlib import Path

from api import llm
from evals.graders import similarity

RUBRIC_FILE = Path(__file__).resolve().parent / "judge_rubric.md"
SUPPORT_MIN = 0.45   # 모의 판정자가 "근거로 뒷받침된다"고 보는 최소 유사도


def split_sentences(text):
    """글을 문장 단위로 자른다. 근거 번호 [n]은 지운다."""
    text = re.sub(r"\[\d+\]", "", text)
    parts = re.split(r"(?<=[다요])\.\s*|\n+", text)
    return [p.strip(" -.") for p in parts if p and len(p.strip(" -.")) >= 4]


def output_text(suite, output):
    """채점할 출력을 글 하나로 만든다."""
    if suite == "summary":
        items = [x for key in ("duties", "qualifications", "cautions") for x in output.get(key, [])]
        return "\n".join(items)
    return output["answer"]


def mock_judge(evidence, text, support_min=SUPPORT_MIN, check_numbers=False):
    """모의 판정: 뒷받침되지 않는 문장이 있으면 fail.

    check_numbers가 참이면 문장 안의 숫자가 근거에 그대로 있는지도 본다(숫자 바꿔치기 탐지).
    """
    evidence_sentences = split_sentences(evidence)
    evidence_numbers = set(re.findall(r"\d+", evidence))
    unsupported = []
    for sentence in split_sentences(text):
        best = max((similarity(sentence, e) for e in evidence_sentences), default=0.0)
        if best < support_min:
            unsupported.append(sentence)
        elif check_numbers and not set(re.findall(r"\d+", sentence)) <= evidence_numbers:
            unsupported.append(sentence)
    if unsupported:
        return "fail", f"근거로 뒷받침되지 않는 문장: {unsupported[0][:40]}"
    return "pass", "모든 문장이 근거와 겹친다"


def build_prompt(evidence, text):
    """기준표 파일로 (시스템 프롬프트, 사용자 프롬프트)를 만든다."""
    raw = RUBRIC_FILE.read_text(encoding="utf-8")
    system_part, user_part = raw.split("### user", 1)
    system = system_part.split("### system", 1)[1].strip()
    prompt = llm.fill(user_part.strip(), {"EVIDENCE": evidence, "OUTPUT": text})
    return system, prompt


def parse_verdict(reply):
    """<result>…</result>에서 판정을 읽는다. 형식이 어긋나면 unknown으로 본다."""
    match = re.search(r"<result>\s*(pass|fail|unknown)\s*</result>", reply)
    reason = re.search(r"<reason>(.*?)</reason>", reply, re.S)
    verdict = match.group(1) if match else "unknown"
    return verdict, (reason.group(1).strip() if reason else reply[:80])


def judge(suite, evidence, output, backend="sim"):
    """출력 하나를 판정해 (판정, 이유)를 돌려준다. 판정은 pass, fail, unknown 가운데 하나다."""
    if output is None:
        return "fail", "출력 없음"
    text = output_text(suite, output)
    if suite == "ask" and output["answer"].strip() == "자료에 없습니다.":
        return "pass", "거절 답은 판정하지 않는다"
    if backend == "real":
        system, prompt = build_prompt(evidence, text)
        return parse_verdict(llm.complete(system, prompt, task="judge"))
    return mock_judge(evidence, text)


# ---------------------------------------------------------------------------
# 쌍 비교(pairwise)와 순서 바꾸기 점검
# ---------------------------------------------------------------------------

def biased_pairwise(evidence, first, second, bias=0.1):
    """위치 편향을 일부러 넣은 모의 쌍 비교 판정자.

    두 출력의 근거 겹침 점수를 재되, 먼저 제시된 쪽에 bias만큼 점수를 더 준다.
    실제 LLM 판정자에게서 보고된 위치 편향(Zheng 외 2023, Wang 외 2023)을 흉내 낸 것이다.
    """
    def score(text):
        sentences = split_sentences(text)
        evidence_sentences = split_sentences(evidence)
        if not sentences:
            return 0.0
        return sum(max((similarity(s, e) for e in evidence_sentences), default=0.0)
                   for s in sentences) / len(sentences)
    a, b = score(first) + bias, score(second)
    return "first" if a >= b else "second"


def swap_check(evidence, x, y, judge_fn=biased_pairwise):
    """x와 y를 두 순서로 물어 두 판정이 같은 쪽을 가리킬 때만 승자를 정한다."""
    forward = judge_fn(evidence, x, y)            # x가 먼저
    backward = judge_fn(evidence, y, x)           # y가 먼저
    winner_forward = "x" if forward == "first" else "y"
    winner_backward = "y" if backward == "first" else "x"
    if winner_forward == winner_backward:
        return winner_forward
    return "tie"


def pairwise_demo():
    """골든 세트 요약 문항에서 원래 요약(x)과 항목 하나를 지어낸 요약(y)을 비교한다."""
    from evals.run import load_golden
    from evals.sim import INVENTED_CAUTION
    items = load_golden("summary")
    counts = {"x_first": 0, "y_first": 0, "swap_x": 0, "swap_y": 0, "swap_tie": 0}
    for item in items:
        refs = [r for key in ("duties", "qualifications", "cautions") for r in item["expect"][key]]
        if not refs:
            continue
        x = "\n".join(refs)
        y = "\n".join(refs[:-1] + [INVENTED_CAUTION])
        evidence = item["input"]
        counts["x_first"] += biased_pairwise(evidence, x, y) == "first"
        counts["y_first"] += biased_pairwise(evidence, y, x) == "first"
        result = swap_check(evidence, x, y)
        counts["swap_" + result] += 1
    total = counts["swap_x"] + counts["swap_y"] + counts["swap_tie"]
    print(f"비교한 문항: {total}")
    print(f"x(충실한 요약)를 먼저 보였을 때 x 승: {counts['x_first']}")
    print(f"y(지어낸 항목이 있는 요약)를 먼저 보였을 때 y 승: {counts['y_first']}")
    print(f"순서 바꾸기 점검: x 승 {counts['swap_x']}, y 승 {counts['swap_y']}, 판정 보류 {counts['swap_tie']}")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):   # Windows Git Bash에서 파이프로 넘겨도 한글이 UTF-8로 나가게(부록 A-4-4)
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    if sys.argv[1:] == ["pairwise-demo"]:
        pairwise_demo()
    else:
        print("사용법: python -m evals.judge pairwise-demo")
        sys.exit(2)
