"""PreToolUse 훅을 견본 입력으로 단독 실행해 본다. Claude Code를 띄우지 않고 훅만 시험하는 도구이다.

hook_samples/의 파일 이름이 block_로 시작하면 막혀야(종료 코드 2) 하고, pass_로 시작하면 통과해야(0) 한다.
gap_samples/의 gap_ 견본은 이 훅이 막지 못하는 것으로 알려진 우회(알려진 틈)이다. 통과되면 「알려진 틈」,
막히면 「틈이 막힘」으로 보여 주며 불일치로 세지 않는다.
견본 안의 __PROJECT__는 저장소 폴더의 절대 경로(슬래시 꼴)로, __PROJECT_WIN__은 Windows 꼴(C:\…, 역슬래시)로,
__LABKEY__는 실행 중에 만든 가짜 키 모양의 값으로 바꾼다(견본 파일에 키 모양을 그대로 적지 않으려는 것이다.
scan_secrets.py가 견본을 비밀로 잡지 않는다). Windows에서 Claude Code는 file_path를 역슬래시 꼴로 넘긴다.

    python security/lab/try_hook.py                          # .claude/hooks/block_secrets.py를 시험
    python security/lab/try_hook.py --samples security/lab/gap_samples   # 알려진 틈 보기
    python security/lab/try_hook.py --hook 다른_훅.py         # 다른 훅을 시험
종료 코드: 기대와 다른 block_·pass_ 견본이 하나라도 있으면 1.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run_sample(hook, sample, root):
    fake_key = "LABKEY-" + "0123456789abcdef" * 2
    text = sample.read_text(encoding="utf-8")
    windows_form = str(root) if os.name == "nt" else "C:" + root.as_posix().replace("/", "\\")
    text = text.replace("__PROJECT_WIN__", json.dumps(windows_form)[1:-1])
    text = text.replace("__PROJECT__", json.dumps(root.as_posix())[1:-1]).replace("__LABKEY__", fake_key)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, str(hook)], input=text, capture_output=True, text=True,
                            encoding="utf-8", env=env, timeout=30)
    return result.returncode, (result.stderr.strip().splitlines() or [""])[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="훅 단독 시험")
    parser.add_argument("--hook", default=".claude/hooks/block_secrets.py")
    parser.add_argument("--root", default=".")
    parser.add_argument("--samples", default=str(HERE / "hook_samples"))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    hook = (root / args.hook).resolve()
    if not hook.exists():
        print(f"훅 파일이 없다: {args.hook}")
        return 1
    wrong = 0
    samples = sorted(Path(args.samples).glob("*.json"))
    for sample in samples:
        expected = 2 if sample.name.startswith("block_") else 0
        code, message = run_sample(hook, sample, root)
        if sample.name.startswith("gap_"):
            mark = "알려진 틈" if code == 0 else "틈이 막힘"
        else:
            ok = code == expected
            wrong += not ok
            mark = "일치" if ok else f"불일치(기대 {expected})"
        print(f"{code}  {mark:<12} {sample.stem:<28} {message[:70]}")
    print(f"견본 {len(samples)}개, 불일치 {wrong}개")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
