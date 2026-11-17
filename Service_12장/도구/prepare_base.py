"""앞 장 산출물이 없는 학습자를 위해 기준 산출물(jobprep)을 개인 실습 저장소에 채운다.

이미 있는 파일은 덮어쓰지 않는다. 무엇을 복사하고 무엇을 건너뛰었는지 보여 준다.

    python 도구/prepare_base.py ~/llm-service-lab            (실제로 복사)
    python 도구/prepare_base.py ~/llm-service-lab --dry-run  (복사할 목록만 본다)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import utf8_stdout  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "기준산출물" / "jobprep"


def main() -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", help="개인 실습 저장소 폴더(예: ~/llm-service-lab)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dest = Path(args.repo).expanduser() / "jobprep"
    copied = skipped = 0
    for src in sorted(SRC.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts or ".pytest_cache" in src.parts or "logs" in src.parts:
            continue
        target = dest / src.relative_to(SRC)
        if target.exists():
            skipped += 1
            continue
        copied += 1
        print(("복사 예정 " if args.dry_run else "복사 ") + str(target.relative_to(dest.parent)))
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    print(f"복사 {copied}개, 이미 있어 건너뜀 {skipped}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
