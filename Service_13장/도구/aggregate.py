"""사용성 테스트의 과업 기록과 문제 목록을 집계한다.

    python aggregate.py tasks 과업기록.csv [--md]      과업별 성공 수준, 소요 시간, 오류 수
    python aggregate.py problems 문제목록.csv [--md]   심각도별 문제 수와 우선순위

과업기록.csv 머리글: 참가자,과업,결과,시간초,오류수
  결과는 다음 넷 중 하나다(NN/g의 성공 수준을 따른다).
    완전성공    과업을 오류 없이 끝냄
    사소한문제  끝냈으나 결과에 작은 흠이 있음(예: 메모 누락)
    큰문제      끝냈으나 결과가 목표와 크게 다름(예: 다른 공고를 저장)
    실패        끝내지 못함, 포기, 시간 초과
  성공 수준은 순서만 있는 범주다. 숫자로 바꾸어 평균 내지 않는다.

문제목록.csv 머리글: ID,문제,출처,휴리스틱,심각도,빈도
  심각도는 0~4(Nielsen의 척도), 빈도는 1~3(1 드묾, 2 가끔, 3 자주)이다.
  우선순위 점수 = 심각도 x 빈도. 점수가 같으면 심각도가 높은 쪽이 앞선다.
  심각도 4(출시 전에 반드시 고칠 문제)는 점수와 관계없이 맨 앞에 둔다.
"""
import csv
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

LEVELS = ["완전성공", "사소한문제", "큰문제", "실패"]
COMPLETED = {"완전성공", "사소한문제", "큰문제"}


class AggregateError(ValueError):
    """입력이 형식에 맞지 않을 때 낸다."""


def _read(path, columns):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise AggregateError(f"머리글에 없는 열: {', '.join(missing)}")
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    if not rows:
        raise AggregateError("자료가 한 줄도 없다")
    return rows


def _int(row, key, line, low=None, high=None):
    text = (row[key] or "").strip()
    try:
        value = int(text)
    except ValueError:
        raise AggregateError(f"{line}번째 줄의 {key}: 정수가 아니다 ({text!r})") from None
    if (low is not None and value < low) or (high is not None and value > high):
        raise AggregateError(f"{line}번째 줄의 {key}: {low}~{high} 범위 밖이다 ({value})")
    return value


def load_tasks(path):
    rows = _read(path, ["참가자", "과업", "결과", "시간초", "오류수"])
    records = []
    for line, row in enumerate(rows, start=2):
        level = (row["결과"] or "").strip()
        if level not in LEVELS:
            raise AggregateError(f"{line}번째 줄의 결과: {level!r}는 {', '.join(LEVELS)} 중 하나가 아니다")
        records.append({
            "참가자": row["참가자"].strip(),
            "과업": row["과업"].strip(),
            "결과": level,
            "시간초": _int(row, "시간초", line, 0),
            "오류수": _int(row, "오류수", line, 0),
        })
    return records


def summarize_tasks(records):
    """과업별로 성공 수준의 수, 완료율, 소요 시간(완료한 시도만), 평균 오류 수를 낸다."""
    by_task = OrderedDict()
    for r in records:
        by_task.setdefault(r["과업"], []).append(r)
    result = []
    for task, rs in by_task.items():
        counts = Counter(r["결과"] for r in rs)
        done_times = [r["시간초"] for r in rs if r["결과"] in COMPLETED]
        result.append({
            "과업": task,
            "n": len(rs),
            "levels": {level: counts.get(level, 0) for level in LEVELS},
            "완료율": sum(counts[l] for l in COMPLETED) / len(rs),
            "완전성공률": counts.get("완전성공", 0) / len(rs),
            "시간_중앙값": statistics.median(done_times) if done_times else None,
            "시간_평균": statistics.fmean(done_times) if done_times else None,
            "오류_평균": statistics.fmean(r["오류수"] for r in rs),
        })
    return result


def load_problems(path):
    rows = _read(path, ["ID", "문제", "출처", "휴리스틱", "심각도", "빈도"])
    problems = []
    for line, row in enumerate(rows, start=2):
        problems.append({
            "ID": row["ID"].strip(),
            "문제": row["문제"].strip(),
            "출처": row["출처"].strip(),
            "휴리스틱": row["휴리스틱"].strip(),
            "심각도": _int(row, "심각도", line, 0, 4),
            "빈도": _int(row, "빈도", line, 1, 3),
        })
    ids = [p["ID"] for p in problems]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated:
        raise AggregateError(f"ID가 겹친다: {', '.join(duplicated)}")
    return problems


def severity_counts(problems):
    counts = Counter(p["심각도"] for p in problems)
    return {level: counts.get(level, 0) for level in (4, 3, 2, 1, 0)}


def prioritize(problems):
    """심각도 0(문제 아님)을 빼고 정렬한다. 심각도 4가 먼저, 그다음은 점수의 내림차순이다."""
    real = [dict(p, 점수=p["심각도"] * p["빈도"]) for p in problems if p["심각도"] > 0]
    return sorted(real, key=lambda p: (p["심각도"] != 4, -p["점수"], -p["심각도"], p["ID"]))


def _sec(value):
    return "-" if value is None else f"{value:.0f}초"


def report_tasks(summary, markdown=False):
    lines = []
    if markdown:
        lines.append("| 과업 | 참가자 | 완전성공 | 사소한문제 | 큰문제 | 실패 | 완료율 | 시간 중앙값(완료) | 평균 오류 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for s in summary:
            lv = s["levels"]
            lines.append(
                f"| {s['과업']} | {s['n']} | {lv['완전성공']} | {lv['사소한문제']} | {lv['큰문제']} | {lv['실패']} "
                f"| {s['완료율']:.0%} | {_sec(s['시간_중앙값'])} | {s['오류_평균']:.1f} |"
            )
    else:
        for s in summary:
            lv = s["levels"]
            lines.append(
                f"{s['과업']}: 참가자 {s['n']}명 | 완전성공 {lv['완전성공']}, 사소한문제 {lv['사소한문제']}, "
                f"큰문제 {lv['큰문제']}, 실패 {lv['실패']} | 완료율 {s['완료율']:.0%} | "
                f"시간 중앙값 {_sec(s['시간_중앙값'])} | 평균 오류 {s['오류_평균']:.1f}"
            )
    n = max(s["n"] for s in summary)
    if n < 5:
        lines.append(f"주의: 과업당 참가자가 {n}명이다. 비율은 '몇 명 중 몇 명'으로 함께 적고 일반화하지 않는다.")
    return "\n".join(lines)


def report_problems(problems, markdown=False):
    counts = severity_counts(problems)
    ranked = prioritize(problems)
    lines = ["심각도별 문제 수: " + ", ".join(f"{k}={v}" for k, v in counts.items())]
    lines.append("")
    if markdown:
        lines.append("| 순위 | ID | 문제 | 출처 | 휴리스틱 | 심각도 | 빈도 | 점수 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for rank, p in enumerate(ranked, start=1):
            lines.append(
                f"| {rank} | {p['ID']} | {p['문제']} | {p['출처']} | {p['휴리스틱']} "
                f"| {p['심각도']} | {p['빈도']} | {p['점수']} |"
            )
    else:
        for rank, p in enumerate(ranked, start=1):
            lines.append(f"{rank:>2}. [{p['점수']:>2}] {p['ID']} (심각도 {p['심각도']} x 빈도 {p['빈도']}) {p['문제']}")
    return "\n".join(lines)


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2 or args[0] not in ("tasks", "problems"):
        print(__doc__)
        return 1
    kind, path = args[0], Path(args[1])
    if not path.exists():
        print(f"파일이 없다: {path}")
        return 1
    markdown = "--md" in argv
    try:
        if kind == "tasks":
            print(report_tasks(summarize_tasks(load_tasks(path)), markdown))
        else:
            print(report_problems(load_problems(path), markdown))
    except AggregateError as e:
        print(f"오류: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
