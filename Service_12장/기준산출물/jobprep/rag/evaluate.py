# -*- coding: utf-8 -*-
"""검색 품질 측정: 재현율@k, 정밀도@k, 적중 수. 기준값 정하기(calibrate).

평가 문항 파일(평가문항.csv)의 열
    번호, 질문, 정답절
정답절은 「문서이름#절 제목」이다. 정답 절이 둘 이상이면 ;로 잇는다.
    예) 현장실습_운영규정#제5조 (실습 기간과 학점);현장실습_운영규정#제15조 (평가)

판정: 상위 k개 청크가 걸쳐 있는 절(chunk["sections"])을 모아 정답 절과 견준다.
청크를 자르는 방식이 달라져도 절을 기준으로 세므로 같은 문항 파일로 비교할 수 있다.
"""
import csv
from pathlib import Path

from . import config, search

DEFAULT_CSV = Path(__file__).resolve().parent / "평가문항.csv"
OUT_OF_SCOPE_CSV = Path(__file__).resolve().parent / "범위밖문항.csv"


def load_questions(path=DEFAULT_CSV):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["정답"] = [g.strip() for g in row.get("정답절", "").split(";") if g.strip()]
    return rows


def retrieved_sections(hits):
    """상위 청크들이 걸쳐 있는 절을 「문서이름#절 제목」 집합으로 모은다."""
    found = set()
    for h in hits:
        for name in h["chunk"]["sections"]:
            found.add(f'{h["chunk"]["source"]}#{name}')
    return found


def recall_at_k(gold, retrieved):
    """정답 절 가운데 검색된 절의 비율(0.0~1.0)을 돌려준다. [실습에서 완성]

    gold는 정답 절 목록, retrieved는 상위 k개에서 모은 절 집합이다.
    재현율 = |정답 ∩ 검색됨| / |정답|. 정답이 비어 있으면 0.0을 돌려준다.
    """
    if not gold:
        return 0.0
    return len(set(gold) & set(retrieved)) / len(set(gold))


def precision_at_k(gold, hits):
    """상위 k개 청크 가운데 정답 절에 걸친 청크의 비율. (완성되어 있음)"""
    if not hits:
        return 0.0
    relevant = sum(1 for h in hits if retrieved_sections([h]) & set(gold))
    return relevant / len(hits)


def run_eval(index, csv_path=DEFAULT_CSV, k=None, method=None):
    k = k or config.top_k()
    rows = []
    for q in load_questions(csv_path):
        hits = search.search(q["질문"], index, k=k, method=method)
        found = retrieved_sections(hits)
        rows.append({
            "번호": q["번호"],
            "질문": q["질문"],
            "정답": q["정답"],
            "recall": recall_at_k(q["정답"], found),
            "precision": precision_at_k(q["정답"], hits),
            "top": [f'{h["chunk"]["source"]}#{h["chunk"]["heading"]}' for h in hits],
        })
    return rows


def summary(rows):
    n = len(rows)
    return {
        "문항": n,
        "적중": sum(1 for r in rows if r["recall"] > 0),
        "재현율": sum(r["recall"] for r in rows) / n,
        "정밀도": sum(r["precision"] for r in rows) / n,
    }


def report(rows, k, method, settings, as_markdown=False):
    s = summary(rows)
    lines = []
    if as_markdown:
        lines.append(f"설정: 검색={method}, k={k}, " + ", ".join(f"{a}={b}" for a, b in settings.items()))
        lines.append("")
        lines.append("| 번호 | 질문 | 재현율 | 정밀도 | 1위 청크의 절 |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            lines.append(f'| {r["번호"]} | {r["질문"]} | {r["recall"]:.2f} | {r["precision"]:.2f} | {r["top"][0]} |')
        lines.append("")
        lines.append(f'재현율@{k} 평균 {s["재현율"]:.2f}, 적중 {s["적중"]}/{s["문항"]}, 정밀도@{k} 평균 {s["정밀도"]:.2f}')
    else:
        for r in rows:
            mark = "O" if r["recall"] == 1 else ("△" if r["recall"] > 0 else "X")
            lines.append(f'{int(r["번호"]):2d}. [{mark}] {r["질문"]}  (1위: {r["top"][0]})')
        lines.append("")
        lines.append(f'재현율@{k} 평균 {s["재현율"]:.2f}  적중 {s["적중"]}/{s["문항"]}  정밀도@{k} 평균 {s["정밀도"]:.2f}')
    return "\n".join(lines)


def calibrate(index, method=None):
    """평가 문항(자료에 있는 질문)과 범위 밖 문항(자료에 없는 질문)의 1위 유사도를 견준다."""
    inside = [max(h["similarity"] for h in search.search(q["질문"], index, method=method))
              for q in load_questions(DEFAULT_CSV)]
    outside_rows = load_questions(OUT_OF_SCOPE_CSV)
    outside = [max(h["similarity"] for h in search.search(q["질문"], index, method=method))
               for q in outside_rows]
    lo_in, hi_out = min(inside), max(outside)
    lines = [
        f"자료에 있는 질문 {len(inside)}개의 1위 유사도: 최저 {lo_in:.4f}, 최고 {max(inside):.4f}",
        f"자료에 없는 질문 {len(outside)}개의 1위 유사도: 최저 {min(outside):.4f}, 최고 {hi_out:.4f}",
    ]
    for q, s in zip(outside_rows, outside):
        lines.append(f"  - {q['질문']}: {s:.4f}")
    if hi_out < lo_in:
        lines.append(f"두 무리가 갈린다. 기준값 후보: {(hi_out + lo_in) / 2:.2f} (두 값의 가운데)")
    else:
        lines.append("두 무리가 겹친다. 기준값만으로는 가를 수 없으므로 프롬프트의 지시가 함께 막아야 한다")
    return "\n".join(lines)
