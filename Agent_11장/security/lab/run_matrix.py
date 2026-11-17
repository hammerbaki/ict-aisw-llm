"""시나리오 넷을 방어층마다 돌려 결과를 마크다운 표로 낸다. security/결과기록.md의 2절에 옮겨 붙인다.

저장소를 더럽히지 않으려고 임시 폴더에 대책 파일(.claude/의 설정·훅·에이전트), security/lab, security/tools,
가짜 키를 복사해 그곳에서 돌린다. 방어가 없는 열(none)이 유출 파일(web/notice.txt 등)을 만들어도 저장소에는
남지 않는다. 감사 기록만 저장소의 security/logs/로 옮겨 온다.

    python security/lab/run_matrix.py
    python security/lab/run_matrix.py --defenses none,rules,hook     # 일부 열만
종료 코드: all 열에서 하나라도 유출되면 1.
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import naive_agent  # noqa: E402

SCENARIOS = sorted(p.name for p in (HERE / "scenarios").iterdir() if p.is_file())
COLUMNS = ["none", "rules", "hook", "tools", "output", "all"]
COPY = [".claude/settings.json", ".claude/hooks/block_secrets.py", ".claude/agents/issue-triage.md",
        naive_agent.SECRET_FILE]


def cell(summary):
    if summary["leaked"]:
        where = ", ".join("응답" if p == "최종 응답" else "바깥 주소" if p.startswith("바깥") else p
                          for p in summary["places"])
        return f"유출({where})"
    return f"막힘({', '.join(summary['blocked_layers']) or '-'})"


def prepare(root, work):
    for rel in COPY:
        if (root / rel).exists():
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / rel, work / rel)
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(root / "security" / "lab", work / "security" / "lab", ignore=ignore)
    shutil.copytree(root / "security" / "tools", work / "security" / "tools", ignore=ignore)


def main(argv=None):
    parser = argparse.ArgumentParser(description="방어층별 재현 결과 표")
    parser.add_argument("--defenses", default=",".join(COLUMNS))
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    columns = [c.strip() for c in args.defenses.split(",") if c.strip()]
    leaks = 0
    with tempfile.TemporaryDirectory(prefix="agt11-") as tmp:
        work = Path(tmp)
        prepare(root, work)
        print("| 시나리오 | " + " | ".join(columns) + " |")
        print("|---" * (len(columns) + 1) + "|")
        for scenario in SCENARIOS:
            row = []
            for column in columns:
                layers = [] if column == "none" else list(naive_agent.LAYERS) if column == "all" else [column]
                summary = naive_agent.run(f"security/lab/scenarios/{scenario}", layers, root=work, quiet=True)
                row.append(cell(summary))
                leaks += summary["leaked"] and column == "all"
            print(f"| {scenario} | " + " | ".join(row) + " |")
        logs = root / "security" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        for log in (work / "security" / "logs").glob("*.jsonl"):
            shutil.copyfile(log, logs / log.name)
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
