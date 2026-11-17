# -*- coding: utf-8 -*-
"""재현율 고정 테스트. 고치지 않는다. recall_at_k를 완성하면 통과한다."""
import pytest

from rag import evaluate


def test_정답_절이_모두_검색되면_재현율은_1이다():
    assert evaluate.recall_at_k(["a#1"], {"a#1", "b#2"}) == pytest.approx(1.0)


def test_정답_절이_없으면_재현율은_0이다():
    assert evaluate.recall_at_k(["a#1"], {"b#2", "c#3"}) == pytest.approx(0.0)


def test_정답_절_둘_가운데_하나만_찾으면_재현율은_절반이다():
    assert evaluate.recall_at_k(["a#1", "a#2"], {"a#1", "c#3"}) == pytest.approx(0.5)


def test_정답이_비어_있으면_0을_돌려준다():
    assert evaluate.recall_at_k([], {"a#1"}) == 0.0


def test_평가_문항은_10개이고_정답_절이_모두_자료에_있다(kit_index):
    rows = evaluate.load_questions()
    assert len(rows) == 10
    sections = {f'{c["source"]}#{s}' for c in kit_index.chunks for s in c["sections"]}
    for row in rows:
        for gold in row["정답"]:
            assert gold in sections, f"{row['번호']}번의 정답 절 {gold}이 색인에 없다"


def test_기본_설정의_재현율은_기록한_값_이상이다(kit_index):
    rows = evaluate.run_eval(kit_index, k=3, method="vector")
    s = evaluate.summary(rows)
    assert s["문항"] == 10
    assert s["재현율"] >= 0.8  # 대체 임베딩, heading 500자 기준 실측 0.90 (2026-11-14)
