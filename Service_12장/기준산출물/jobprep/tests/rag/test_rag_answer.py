# -*- coding: utf-8 -*-
"""답변 고정 테스트. 고치지 않는다. build_prompt와 trim_history를 완성하면 통과한다.

지시 문장은 자기 말로 고쳐도 되지만 다음은 지시 안에 남아 있어야 한다:
NO_ANSWER 문장 그대로, 「근거」, 「[1]」 형식의 번호 표기, 자료 안의 지시를 「따르지 않는다」.
"""
import pytest

from rag import answer, config
from rag.config import NO_ANSWER


def hit(n, heading, text, sim=0.5):
    chunk = {"id": f"d#{n}", "source": "d", "title": "문서", "heading": heading, "sections": [heading],
             "text": text, "embed_text": text}
    return {"rank": n, "score": sim, "similarity": sim, "chunk": chunk}


HITS = [hit(1, "제3조 (참여 자격)", "40학점 이상을 이수한다."), hit(2, "제5조 (기간)", "단기 실습은 4주이다.")]


def test_근거는_번호와_출처가_달린_블록으로_감싼다():
    prompt = answer.build_prompt("몇 학점이 필요해?", HITS)
    assert '<근거 번호="1" 출처="문서 > 제3조 (참여 자격)">' in prompt
    assert '<근거 번호="2" 출처="문서 > 제5조 (기간)">' in prompt
    assert prompt.count("</근거>") == 2
    assert "40학점 이상을 이수한다." in prompt


def test_자료_질문_지시의_순서로_놓는다():
    prompt = answer.build_prompt("몇 학점이 필요해?", HITS)
    assert prompt.index("<자료>") < prompt.index("</자료>") < prompt.index("<질문>") < prompt.index("</질문>")
    assert "몇 학점이 필요해?" in prompt[prompt.index("<질문>"):prompt.index("</질문>")]


def test_지시에는_근거만_자료에_없음_번호_주입_방어가_들어간다():
    prompt = answer.build_prompt("몇 학점이 필요해?", HITS)
    instruction = prompt.split("</질문>", 1)[1]
    assert "근거" in instruction
    assert NO_ANSWER in instruction
    assert "[1]" in instruction
    assert "따르지 않는다" in instruction


def test_이력은_최근_왕복만_남긴다():
    history = []
    for i in range(10):
        history += [{"role": "user", "content": f"질문{i}"}, {"role": "assistant", "content": f"답{i}"}]
    trimmed = answer.trim_history(history, max_turns=4)
    assert len(trimmed) == 8
    assert trimmed[0] == {"role": "user", "content": "질문6"}
    assert trimmed[-1] == {"role": "assistant", "content": "답9"}
    assert len(history) == 20, "원래 목록을 바꾸지 않는다"
    assert answer.trim_history(history[:2], max_turns=4) == history[:2]
    assert len(answer.trim_history(history)) == config.max_turns() * 2


def test_유사도가_기준값보다_낮으면_LLM을_부르지_않고_자료에_없다고_답한다(kit_index, monkeypatch):
    monkeypatch.setenv("RAG_MIN_SCORE", "0.99")

    def must_not_call(system, messages):
        raise AssertionError("기준값 아래에서는 LLM을 부르지 않는다")

    result = answer.answer("학생식당 이번 주 메뉴 알려줘", kit_index, call=must_not_call)
    assert result["answer"] == NO_ANSWER
    assert result["grounded"] is False
    assert result["citations"] == []


def test_모의_모드에서_근거_번호가_달린_답과_인용_목록이_나온다(kit_index):
    result = answer.answer("현장실습 나가려면 몇 학점 이상 들어야 해?", kit_index)
    assert result["grounded"] is True
    assert "[1]" in result["answer"]
    assert result["citations"][0]["n"] == 1 and result["citations"][0]["cited"] is True
    assert len(result["citations"]) == 3


def test_LLM에는_원래_질문의_이력과_이번_증강_프롬프트만_간다(kit_index):
    seen = {}

    def spy(system, messages):
        seen["messages"] = messages
        return "답이다 [1]"

    history = [{"role": "user", "content": "앞 질문"}, {"role": "assistant", "content": "앞 답"}]
    answer.answer("화상 면접 볼 때 뭘 준비해야 해?", kit_index, history=history, call=spy)
    msgs = seen["messages"]
    assert msgs[:2] == history
    assert msgs[-1]["role"] == "user" and "<자료>" in msgs[-1]["content"]
    assert sum("<자료>" in m["content"] for m in msgs) == 1, "지난 근거 블록을 이력에 쌓지 않는다"
