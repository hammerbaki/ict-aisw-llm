"""변동 모의 모델: 평가 실습을 API 키 없이 하기 위한 교육용 모의 모델이다.

기준 저장소의 모의 모드(api/llm.py의 fake_reply)는 같은 입력에 언제나 같은 답을 내고,
프롬프트 판본이 바뀌어도 답이 같다. 그래서 반복 실행의 분산이나 판본 비교를 연습할 수 없다.
이 모듈은 fake_reply의 답에 다음 두 가지를 더한다.

1. 판본 민감성: 프롬프트에 특정 규칙 문장이 있는지에 따라 실수할 확률이 달라진다.
   (예: "우대 사항은 자격 요건에 넣지 않는다"가 없으면 우대 사항을 자격 요건에 섞는 일이 잦다)
2. 결정적 변동: (모델 이름, 반복 번호, 프롬프트 전체)로 난수 씨앗을 만든다. 같은 조건이면
   어느 컴퓨터에서나 같은 결과가 나오고, 반복 번호가 다르면 결과가 달라진다.

여기의 확률은 실제 모델을 잰 값이 아니라 집필자가 정한 값이다. 이 모의 모델의 점수로
실제 모델의 품질을 말할 수 없다. 실제 점수는 --backend real로 따로 재야 한다.
"""

import hashlib
import json
import logging
import math
import random
import re

from api import llm

logger = logging.getLogger("jobprep.llm")

# 프롬프트 안에서 찾는 규칙 문장. 문장이 있으면 그 규칙을 지킨다고 본다.
RULE_PREFERRED = "우대 사항은 자격 요건에 넣지 않는다"
RULE_LENGTH = "40자 이내"
RULE_DEADLINE = "서류 접수 마감일"
RULE_CAUTION_FIRST = "주의점으로 먼저"
RULE_NO_INVENT = "공고에 없는 주의점은 쓰지 않는다"
RULE_CITE = "근거 번호를 [1]처럼"

INVENTED_CAUTION = "지원 전에 회사 홈페이지에서 인재상을 확인한다"
LONG_TAIL = ", 그리고 관련 부서와 협의하여 일정과 결과를 정리해 주기적으로 보고하는 일까지 함께 맡는다"
EXTRA_SENTENCE = " 신청은 휴대전화 앱으로도 언제든 바로 처리된다."

# 모델 성향표. sim-a는 기본 모델, sim-b는 "모델을 바꾸었다"를 흉내 내는 다른 성향이다.
PROFILES = {
    "sim-a": {
        "fence": 0.05,          # JSON을 코드 블록 표시로 감싼다(읽기는 된다)
        "broken": 0.03,         # JSON이 중간에 끊긴다(구조 실패)
        "omit": 0.04,           # 항목 두 개를 빠뜨린다
        "preferred": (0.03, 0.25),   # (규칙 있음, 규칙 없음) 우대 사항을 자격 요건에 섞을 확률
        "long": (0.02, 0.15),        # 항목 하나를 길게 늘일 확률
        "deadline_fix": (0.9, 0.3),  # 마감일이 여럿일 때 서류 접수 마감일을 고를 확률
        "invent": 0.25,         # 주의점을 먼저 꼽으라는 규칙이 있을 때 공고에 없는 주의점을 지어낼 확률
        "invent_guarded": 0.02, # 지어내지 말라는 규칙도 함께 있을 때의 확률
        "cite_drop": (0.05, 0.5),    # 근거 번호를 빠뜨릴 확률
        "extra": 0.06,          # 근거에 없는 문장을 덧붙일 확률
    },
    "sim-b": {
        "fence": 0.01,
        "broken": 0.01,
        "omit": 0.02,
        "preferred": (0.01, 0.20),
        "long": (0.01, 0.10),
        "deadline_fix": (0.95, 0.4),
        "invent": 0.15,
        "invent_guarded": 0.01,
        "cite_drop": (0.02, 0.4),
        "extra": 0.20,
    },
}


def seed_for(model, run, task, system, prompt):
    """조건이 같으면 같은 씨앗을 만든다. 파이썬의 hash()는 실행마다 달라 쓰지 않는다."""
    key = f"{model}|{run}|{task}|{system}|{prompt}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:16], 16)


def estimate_tokens(text):
    """토큰 수를 글자 수의 절반으로 어림한다. 실제 토크나이저의 값이 아니다."""
    return math.ceil(len(text) / 2)


def make_complete(model="sim-a", run=0):
    """llm.complete와 같은 모양의 함수를 만들어 돌려준다. 평가 실행기가 llm.complete 자리에 끼운다."""
    if model not in PROFILES:
        raise ValueError(f"모의 모델 이름이 아니다: {model} (가능: {', '.join(PROFILES)})")
    p = PROFILES[model]

    def complete(system, prompt, task):
        rng = random.Random(seed_for(model, run, task, system, prompt))
        base = llm.fake_reply(prompt, task)
        if task == "summary":
            text = _perturb_summary(base, system + "\n" + prompt, rng, p)
        elif task == "ask":
            text = _perturb_ask(prompt, rng, p)
        else:
            text = base
        logger.info("task=%s model=%s input_tokens=%d output_tokens=%d",
                    task, model, estimate_tokens(system + prompt), estimate_tokens(text))
        return text

    return complete


def _chance(rng, rate):
    return rng.random() < rate


def _pick(pair, has_rule):
    """(규칙 있음, 규칙 없음) 쌍에서 해당하는 확률을 고른다."""
    return pair[0] if has_rule else pair[1]


def _bullets(text, heading):
    items, inside = [], False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            inside = line == f"[{heading}]"
            continue
        if inside and line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _perturb_summary(base, prompt, rng, p):
    data = json.loads(base)
    job = re.search(r"<공고>(.*?)</공고>", prompt, re.S)
    job_text = job.group(1) if job else prompt

    # 1. 우대 사항을 자격 요건에 섞는다
    preferred = _bullets(job_text, "우대 사항")
    if preferred and _chance(rng, _pick(p["preferred"], RULE_PREFERRED in prompt)):
        data["qualifications"] = (data["qualifications"] + [preferred[0]])[:5]

    # 2. 항목을 길게 늘인다
    if data["duties"] and _chance(rng, _pick(p["long"], RULE_LENGTH in prompt)):
        data["duties"][0] = data["duties"][0] + LONG_TAIL

    # 3. 마감일이 여럿이면 서류 접수 마감일을 고를지 정한다
    paper = re.search(r"서류[^\n]*?마감[^\n]*?(\d{4}-\d{2}-\d{2})", job_text)
    if paper and paper.group(1) != data["deadline"]:
        if _chance(rng, _pick(p["deadline_fix"], RULE_DEADLINE in prompt)):
            data["deadline"] = paper.group(1)

    # 4. 주의점을 먼저 꼽으라는 규칙은 공고에 없는 주의점을 지어내게 만들 수 있다
    if RULE_CAUTION_FIRST in prompt:
        rate = p["invent_guarded"] if RULE_NO_INVENT in prompt else p["invent"]
        if _chance(rng, rate):
            data["cautions"] = ([INVENTED_CAUTION] + data["cautions"])[:5]

    # 5. 판본과 관계없는 잡음
    if _chance(rng, p["omit"]):
        data["duties"] = data["duties"][:-1]
        data["cautions"] = data["cautions"][:-1]
    text = json.dumps(data, ensure_ascii=False)
    if _chance(rng, p["broken"]):
        return text[: len(text) // 2]
    if _chance(rng, p["fence"]):
        return "```json\n" + text + "\n```"
    return text


def _sentences(block):
    lines = [line.strip() for line in block.strip().splitlines()]
    body = " ".join(line for line in lines if line and not line.startswith("#"))
    return [s.strip() for s in re.split(r"(?<=다\.)\s", body) if s.strip()]


def _perturb_ask(prompt, rng, p):
    """근거 가운데 질문과 가장 많이 겹치는 문장을 답으로 고르고 그 근거 번호를 붙인다."""
    from evals.graders import similarity

    question = re.search(r"<질문>(.*?)</질문>", prompt, re.S)
    question = question.group(1).strip() if question else ""
    unit = re.search(r"몇\s*([가-힣])", question)
    unit = unit.group(1) if unit else ("원" if "얼마" in question else None)
    asks_when = "언제" in question
    best = (-1.0, None, None)
    for number, block in re.findall(r"<근거 (\d+)>(.*?)</근거 \d+>", prompt, re.S):
        for sentence in _sentences(block):
            score = similarity(question, sentence)
            # 수량을 묻는 질문에는 같은 단위의 수가 있는 문장을, 때를 묻는 질문에는 날짜가 있는 문장을 고르는 경향
            if unit and re.search(r"(\d+|한|두|세|네)\s*만?\s*" + unit, sentence):
                score += 0.3
            elif asks_when and re.search(r"\d+월|째 주", sentence):
                score += 0.3
            if score > best[0]:
                best = (score, sentence, int(number))
    if best[1] is None:
        return "자료에 없습니다."
    answer = best[1]
    if _chance(rng, p["extra"]):
        answer += EXTRA_SENTENCE
    if not _chance(rng, _pick(p["cite_drop"], RULE_CITE in prompt)):
        answer += f" [{best[2]}]"
    return answer
