"""취업 자료 질의응답(RAG): 검색 → 근거 판정 → 증강 프롬프트 → 생성."""

import os
import re

from api import llm
from rag.index import get_index
from rag.search import search

NOT_FOUND = "자료에 없습니다."
TOP_K = 3

# 1위 청크의 유사도가 이 값보다 낮으면 LLM을 부르지 않고 NOT_FOUND로 답한다.
# 임베딩 방식마다 유사도의 눈금이 달라 기준값을 따로 둔다. 환경 변수 ASK_MIN_SCORE로 바꿀 수 있다.
MIN_SCORE = {"ollama": 0.5, "fallback": 0.3}


def min_score(backend):
    if "ASK_MIN_SCORE" in os.environ:
        return float(os.environ["ASK_MIN_SCORE"])
    return MIN_SCORE[backend]


def build_context(results):
    """검색 결과를 <근거 n> 태그로 감싼 글로 만든다. 번호는 1부터 센다."""
    blocks = []
    for number, item in enumerate(results, 1):
        blocks.append(f"<근거 {number}>\n{item['chunk']['text']}\n</근거 {number}>")
    return "\n\n".join(blocks)


def cited_numbers(answer):
    """답에서 [1], [2]처럼 쓴 근거 번호를 순서대로, 중복 없이 뽑는다."""
    numbers = []
    for found in re.findall(r"\[(\d+)\]", answer):
        number = int(found)
        if number not in numbers:
            numbers.append(number)
    return numbers


def answer_question(question):
    """질문에 답하고 dict를 돌려준다.

    돌려주는 값: answer(답), sources(답이 인용한 근거 목록), prompt_version, model.
    sources의 항목: no(답 안의 근거 번호), source(파일 이름), title(문서와 절 제목), score(유사도).
    """
    index = get_index()
    results = search(question, index, top_k=TOP_K)
    version = llm.prompt_version("ask")
    if not results or results[0]["score"] < min_score(index["backend"]):
        return {"answer": NOT_FOUND, "sources": [], "prompt_version": version, "model": None}

    system, template = llm.load_prompt(version)
    prompt = llm.fill(template, {"CONTEXT": build_context(results), "QUESTION": question})
    answer = llm.complete(system, prompt, task="ask").strip()

    sources = []
    if NOT_FOUND not in answer:
        for number in cited_numbers(answer):
            if 1 <= number <= len(results):
                item = results[number - 1]
                sources.append({
                    "no": number,
                    "source": item["chunk"]["source"],
                    "title": item["chunk"]["title"],
                    "score": item["score"],
                })
    return {"answer": answer, "sources": sources, "prompt_version": version, "model": llm.model_name()}
