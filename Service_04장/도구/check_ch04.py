"""4장 산출물 점검기.

조사 보고의 형식(출처 기호, 가정 기호, 비교표의 크기, 포지셔닝 그림, 가치 제안의 칸,
출처 대조의 판정)을 검사한다. 수치가 원문과 맞는지는 검사하지 못한다. 그 일은 사람이
원문을 열어 출처대조.md에 기록한다.

사용법 (저장소 루트 ~/llm-service-lab 에서)
    python ~/kits/Service_04장/도구/check_ch04.py all ch04          완료 기준 전체
    python ~/kits/Service_04장/도구/check_ch04.py scan ch04/시장조사.md   출처 없는 수치 찾기
    python ~/kits/Service_04장/도구/check_ch04.py table ch04/경쟁서비스_비교표.md
    python ~/kits/Service_04장/도구/check_ch04.py audit ch04/시장조사.md ch04/출처대조.md

종료 코드: 모든 검사를 통과하면 0, 하나라도 미통과면 1, 파일이 없으면 2.
"""
import re
import sys
from pathlib import Path

SOURCE_TAG = re.compile(r"\[(S\d+)\]")
ASSUME_TAG = re.compile(r"\[(?:가정 )?(A\d+)\]")
# 수치: 숫자 뒤에 단위가 붙은 것. 연도(2026년), 날짜(2026-11-14), 절 번호(4-2)는 수치로 보지 않는다.
NUMBER = re.compile(
    r"(?<![\w.\-])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?"
    r"(%p|%|천\s?명|만\s?명|명|개교|개월|만\s?원|억\s?원|원|배|곳|건)"
)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
URL = re.compile(r"https?://[^\s|)>]+")
VERDICTS = ("일치", "불일치", "확인 불가")
COORD = re.compile(r"0(?:\.\d+)?|1")  # mermaid 11.17에서 확인: 1.0, 1.00, .5 는 문법 오류
CELL_OK = ("○", "△", "-")
VALUE_SECTIONS = ("고객 업무", "불편", "이득", "제품·서비스", "불편 해소", "이득 창출", "가치 제안 문장")


def read(path):
    p = Path(path)
    if not p.exists():
        print(f"[없음] {path}")
        sys.exit(2)
    return p.read_text(encoding="utf-8")


def strip_code(text):
    """코드 블록 밖의 줄만 (줄 번호, 줄) 로 돌려준다."""
    out, in_code = [], False
    for no, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            out.append((no, line))
    return out


def tables(text):
    """마크다운 표를 [머리줄, 행들] 목록으로 돌려준다. 행은 칸의 목록이다."""
    result, current = [], []
    for _, line in strip_code(text) + [(0, "")]:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            current.append([c.strip() for c in s.strip("|").split("|")])
        else:
            if len(current) >= 2 and re.fullmatch(r"[-: ]+", "".join(current[1])):
                result.append((current[0], current[2:]))
            current = []
    return result


def find_table(text, *words):
    for head, rows in tables(text):
        joined = " ".join(head)
        if all(w in joined for w in words):
            return head, rows
    return None, []


def source_rows(text):
    head, rows = find_table(text, "기호", "주소", "확인")
    if head is None:
        return {}
    i_url = next(i for i, h in enumerate(head) if "주소" in h)
    i_date = next(i for i, h in enumerate(head) if "확인" in h)
    found = {}
    for r in rows:
        if r and re.fullmatch(r"S\d+", r[0]):
            url = r[i_url] if i_url < len(r) else ""
            date = r[i_date] if i_date < len(r) else ""
            found[r[0]] = (url, date)
    return found


def assumption_ids(text):
    head, rows = find_table(text, "기호", "가정")
    if head is None:
        return set()
    return {r[0] for r in rows if r and re.fullmatch(r"A\d+", r[0])}


def scan(text):
    """출처 없는 수치와 정의되지 않은 기호를 찾는다. (문제 목록, 출처가 붙은 수치 수)"""
    problems = []
    sources = source_rows(text)
    assumes = assumption_ids(text)
    src_head, _ = find_table(text, "기호", "주소", "확인")
    asm_head, _ = find_table(text, "기호", "가정")
    sourced = 0
    used = set()
    for no, line in strip_code(text):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")] if s.startswith("|") else None
        if cells is not None and (cells == src_head or cells == asm_head):
            continue
        if cells and re.fullmatch(r"[SA]\d+", cells[0]):
            continue  # 출처 표와 가정 표의 행
        tags = SOURCE_TAG.findall(s)
        atags = ASSUME_TAG.findall(s)
        used.update(tags)
        for t in tags:
            if t not in sources:
                problems.append(f"{no}행: 출처 표에 없는 기호 [{t}]")
        for t in atags:
            if t not in assumes:
                problems.append(f"{no}행: 가정 표에 없는 기호 [{t}]")
        numbers = [m.group(0) for m in NUMBER.finditer(DATE.sub("", s))]
        if not numbers:
            continue
        if tags:
            sourced += len(numbers)
        elif not atags and "계산" not in s:
            problems.append(f"{no}행: 출처·가정 기호가 없는 수치 {', '.join(numbers)}")
    for key, (url, date) in sorted(sources.items()):
        if not URL.search(url):
            problems.append(f"출처 {key}: 주소가 없다")
        if not DATE.search(date):
            problems.append(f"출처 {key}: 확인 날짜(YYYY-MM-DD)가 없다")
        if key not in used:
            problems.append(f"출처 {key}: 본문에서 쓰이지 않았다 (참고)")
    return problems, sourced


def check_table(text, min_services=5, min_rows=10):
    """첫 번째 비교표: 서비스 열 수, 기능 행 수, 칸의 기호를 검사한다."""
    problems = []
    all_tables = tables(text)
    if not all_tables:
        return ["표가 없다"], 0, 0
    head, rows = all_tables[0]
    services = [h for h in head[1:] if h and "비고" not in h and "근거" not in h]
    n_cols = len(services)
    if n_cols < min_services:
        problems.append(f"서비스 열이 {n_cols}개다 ({min_services}개 이상 필요)")
    if len(rows) < min_rows:
        problems.append(f"기능 행이 {len(rows)}개다 ({min_rows}개 이상 필요)")
    for r in rows:
        for name, cell in zip(services, r[1:1 + n_cols]):
            mark = cell.split()[0] if cell.split() else ""
            if mark not in CELL_OK:
                problems.append(f"'{r[0]}' 행 '{name}' 칸의 값 '{cell}'이 ○ △ - 가 아니다")
    if "확인" not in text or not DATE.search(text):
        problems.append("관찰한 날짜(YYYY-MM-DD)가 없다")
    return problems, n_cols, len(rows)


def check_positioning(text, min_points=6):
    problems = []
    blocks = re.findall(r"```mermaid\s*\n(.*?)```", text, re.S)
    chart = next((b for b in blocks if b.lstrip().startswith("quadrantChart")), None)
    if chart is None:
        return ["mermaid quadrantChart 블록이 없다"], 0
    for key in ("x-axis", "y-axis"):
        if key not in chart:
            problems.append(f"{key} 줄이 없다")
    points = re.findall(r"^\s*([^\n:]+?)\s*:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]", chart, re.M)
    for name, x, y in points:
        if not (0 <= float(x) <= 1 and 0 <= float(y) <= 1):
            problems.append(f"점 '{name}'의 좌표가 0~1 밖이다")
        for v in (x, y):
            if not COORD.fullmatch(v):
                problems.append(f"점 '{name}'의 좌표 {v}: mermaid 11은 1.0과 .5 같은 표기를 받지 않는다. 1 또는 0.5로 쓴다")
    if len(points) < min_points:
        problems.append(f"점이 {len(points)}개다 ({min_points}개 이상: 경쟁 서비스 5개와 공통 사례)")
    if not re.search(r"근거|규칙|점수", text):
        problems.append("좌표를 정한 규칙(근거)이 적혀 있지 않다")
    return problems, len(points)


def check_value(text):
    problems = []
    headings = [line for _, line in strip_code(text) if line.startswith("#")]
    for sec in VALUE_SECTIONS:
        if not any(sec in h for h in headings):
            problems.append(f"'{sec}' 제목이 없다")
    return problems


def audit(report_text, audit_text):
    """조사 보고의 출처 기호마다 대조 기록이 있고, 모든 행에 판정이 있는지 검사한다."""
    problems = []
    used = set(SOURCE_TAG.findall(report_text))
    head, rows = find_table(audit_text, "판정")
    if head is None:
        return ["판정 열이 있는 대조표가 없다"], 0
    i_v = next(i for i, h in enumerate(head) if "판정" in h)
    i_s = next((i for i, h in enumerate(head) if "출처" in h), None)
    covered = set()
    for r in rows:
        if not any(r):
            continue
        verdict = r[i_v] if i_v < len(r) else ""
        if not any(verdict.startswith(v) for v in VERDICTS):
            problems.append(f"'{' '.join(r[:2])}' 행의 판정 '{verdict}'이 일치·불일치·확인 불가가 아니다")
        if i_s is not None and i_s < len(r):
            covered.update(re.findall(r"S\d+", r[i_s]))
    for t in sorted(used - covered):
        problems.append(f"출처 {t}의 대조 기록이 없다")
    return problems, len(rows)


def unfilled(name, text):
    """양식의 「 」 자리가 든 줄이 고쳐지지 않고 그대로 남아 있으면 그 줄 번호를 돌려준다."""
    template = Path(__file__).resolve().parents[1] / f"{name}_양식.md"
    if not template.exists():
        return []
    marks = {t.strip() for t in template.read_text(encoding="utf-8").splitlines() if "「" in t}
    return [no for no, line in enumerate(text.splitlines(), 1) if line.strip() in marks]


def with_unfilled(name, text, problems):
    rows = unfilled(name, text)
    if rows:
        problems.append(f"양식의 「 」 자리가 그대로 남은 줄 {len(rows)}개 (처음: {rows[0]}행)")
    return problems


def report(title, problems, ok_note):
    real = [p for p in problems if not p.endswith("(참고)")]
    mark = "통과" if not real else "미통과"
    print(f"[{mark}] {title} - {ok_note}")
    for p in problems:
        print(f"    {p}")
    return not real


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "scan":
        problems, n = scan(read(args[0]))
        return 0 if report("출처 없는 수치", problems, f"출처가 붙은 수치 {n}개") else 1
    if cmd == "table":
        problems, c, r = check_table(read(args[0]))
        return 0 if report("기능 비교표", problems, f"서비스 {c}개, 기능 {r}행") else 1
    if cmd == "audit":
        problems, n = audit(read(args[0]), read(args[1]))
        return 0 if report("출처 대조", problems, f"대조 기록 {n}행") else 1
    if cmd == "all":
        d = Path(args[0])
        ok = True
        text = {n: read(d / f"{n}.md") for n in ("시장조사", "경쟁서비스_비교표", "포지셔닝", "가치제안", "출처대조")}
        problems, n = scan(text["시장조사"])
        if n < 3:
            problems.append(f"출처가 붙은 수치가 {n}개다 (3개 이상 필요)")
        with_unfilled("시장조사", text["시장조사"], problems)
        ok &= report("1. 시장조사.md", problems, f"출처가 붙은 수치 {n}개")
        problems, c, r = check_table(text["경쟁서비스_비교표"])
        with_unfilled("경쟁서비스_비교표", text["경쟁서비스_비교표"], problems)
        ok &= report("2. 경쟁서비스_비교표.md", problems, f"서비스 {c}개, 기능 {r}행")
        problems, p = check_positioning(text["포지셔닝"])
        with_unfilled("포지셔닝", text["포지셔닝"], problems)
        ok &= report("3. 포지셔닝.md", problems, f"점 {p}개")
        problems = with_unfilled("가치제안", text["가치제안"], check_value(text["가치제안"]))
        ok &= report("4. 가치제안.md", problems, "칸 7개")
        problems, n = audit(text["시장조사"], text["출처대조"])
        with_unfilled("출처대조", text["출처대조"], problems)
        ok &= report("5. 출처대조.md", problems, f"대조 기록 {n}행")
        print("결과:", "완료 기준 통과" if ok else "미통과 항목이 있다")
        return 0 if ok else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
