"""인터뷰 기록에 줄 번호를 붙인다.

인터뷰 중에는 `## 기록` 아래에 화자 표시만 붙여 적는다.

    Q: 요즘 공고는 어디서 보나?
    A: 주로 휴대폰으로 본다.

이 스크립트를 실행하면 번호가 없는 줄에 L 번호를 붙인다.

    L1 Q: 요즘 공고는 어디서 보나?
    L2 A: 주로 휴대폰으로 본다.

사용법
    python number_lines.py ch05/기록/인터뷰_01.md          번호를 붙여 파일을 고친다
    python number_lines.py ch05/기록/인터뷰_01.md --check  고치지 않고 형식만 검사한다

규칙
- 이미 붙은 번호는 바꾸지 않는다. 페르소나가 그 번호를 인용하기 때문이다.
- 새 줄은 기록의 끝에만 덧붙인다. 번호가 붙은 줄 사이에 새 줄이 있으면 멈춘다.
- 화자 표시(Q, A, 관찰, 메모)가 없는 줄은 고치지 않고 알린다.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recordfmt import HEADING2, NUMBERED, SECTION_TITLE, UNNUMBERED  # noqa: E402


def number(lines):
    """(새 줄 목록, 새로 붙인 개수, 알림 목록)을 돌려준다. 규칙 위반은 ValueError."""
    out = list(lines)
    notes = []
    inside = False
    seen_title = False
    numbered = []          # (줄 위치, 번호)
    pending = []           # 번호가 없는 화자 줄의 위치
    for idx, line in enumerate(lines):
        m = HEADING2.match(line)
        if m:
            inside = m.group(1).strip() == SECTION_TITLE
            seen_title = seen_title or inside
            continue
        if not inside or not line.strip() or line.lstrip().startswith(">"):
            continue  # 제목 밖, 빈 줄, 안내 인용문은 건너뛴다
        text = line.strip()
        n = NUMBERED.match(text)
        if n:
            if pending:
                raise ValueError(
                    f"{pending[0] + 1}행: 번호가 붙은 줄(L{n.group(1)}) 앞에 번호 없는 새 줄이 있다. "
                    "새 줄은 기록의 끝에 덧붙인다")
            numbered.append((idx, int(n.group(1))))
            continue
        if UNNUMBERED.match(text):
            pending.append(idx)
            continue
        notes.append(f"{idx + 1}행: 화자 표시(Q, A, 관찰, 메모)가 없는 줄이다: {text[:40]}")
    if not seen_title:
        raise ValueError(f"'## {SECTION_TITLE}' 제목이 없다")
    nums = [n for _, n in numbered]
    for a, b in zip(nums, nums[1:]):
        if b <= a:
            raise ValueError(f"번호가 차례대로가 아니다: L{a} 다음에 L{b}")
    nxt = (max(nums) if nums else 0) + 1
    for idx in pending:
        out[idx] = f"L{nxt} {lines[idx].strip()}"
        nxt += 1
    return out, len(pending), notes


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="인터뷰 기록에 줄 번호를 붙인다")
    parser.add_argument("record", help="기록 파일 (예: ch05/기록/인터뷰_01.md)")
    parser.add_argument("--check", action="store_true", help="파일을 고치지 않고 검사만 한다")
    args = parser.parse_args(argv)
    path = Path(args.record)
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        new_lines, added, notes = number(lines)
    except ValueError as e:
        print(f"[멈춤] {path.name}: {e}")
        return 1
    for note in notes:
        print(f"[알림] {note}")
    total = sum(1 for l in new_lines if NUMBERED.match(l.strip()))
    if args.check:
        state = "번호 없는 줄 없음" if added == 0 else f"번호 없는 줄 {added}개"
        print(f"{path.name}: 번호 붙은 줄 {total - added}개, {state}")
        return 0 if added == 0 else 1
    if added:
        # Windows에서도 줄 끝을 LF로 쓴다(write_text는 CRLF로 바꾼다)
        path.write_bytes(("\n".join(new_lines) + "\n").encode("utf-8"))
    print(f"{path.name}: 새로 번호를 붙인 줄 {added}개, 전체 {total}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
