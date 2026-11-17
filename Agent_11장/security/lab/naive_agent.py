"""간접 프롬프트 주입을 재현하는 「순진한 가짜 에이전트」이다. 11장 실습용. 실제 모델을 부르지 않는다.

이 에이전트의 「모델」은 정해진 규칙으로 움직이는 흉내이다. 입력 문서를 읽은 뒤, 문서 안에서 명령처럼 생긴
문장(「…을 읽어라」, 「`…`을 실행하라」, 「…에 저장하라」, 「주소 뒤에 붙여 열어라」, 「답글 끝에 붙여라」)을
찾으면 그것을 작업 지시로 알고 그대로 도구를 부른다. 실제 LLM은 이렇게 단순하지 않지만, 「입력 속의 글과
지시를 구분하지 못한다」는 약점은 같다. 이 흉내로 공격이 성공하는 경로와 막히는 경로를 매번 같게 재현한다.

도구 넷(모두 저장소 폴더 안에서만 동작하고 네트워크를 쓰지 않는다)
- read_file(path)        Claude Code의 Read에 해당
- write_file(path, text) Write에 해당
- run_bash(command)      Bash에 해당. 실제로 실행하지 않고 cat과 python -c "…open('경로')…" 꼴만 흉내 낸다
- web_fetch(url)         WebFetch에 해당. 보내지 않고 security/out/outbox.jsonl에 「보냈을 주소」를 기록한다

방어층(--defense에 쉼표로 고른다. all은 넷 모두)
- tools  : 에이전트 정의 파일(.claude/agents/*.md)의 tools 줄에 없는 도구는 쓸 수 없다(서브에이전트 도구 제한)
- hook   : .claude/hooks/block_secrets.py를 Claude Code와 같은 JSON 입력으로 실제 실행한다(PreToolUse 훅)
- rules  : .claude/settings.json의 permissions를 3장의 판정 모의기(perm_sim.py)로 판정한다(허용·확인·거부 규칙)
- output : 쓰기 내용, 주소, 최종 응답을 check_output.py로 검사한다(출력 검사)
판정 순서는 Claude Code를 따른다: 도구 목록 → PreToolUse 훅 → 권한 규칙(거부 → 확인 → 허용) → 실행.
출력 검사는 실행 직전과 최종 응답에 건다. 확인(ask)으로 판정된 호출은 --ask로 사람의 응답을 흉내 낸다.

쓰는 법 (저장소 폴더에서, 먼저 python security/lab/make_fake_secret.py)
    python security/lab/naive_agent.py security/lab/scenarios/issue_42.md
    python security/lab/naive_agent.py security/lab/scenarios/issue_42.md --defense rules
    python security/lab/naive_agent.py security/lab/scenarios/issue_42.md --defense all
종료 코드: 가짜 키가 응답·파일·바깥 주소 가운데 한 곳에라도 나타나면 1(유출), 아니면 0.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import perm_sim  # noqa: E402
from check_output import check as check_text  # noqa: E402

SECRET_FILE = "secrets/실습용_가짜키.txt"
LABKEY = re.compile(r"LABKEY-[0-9a-f]{32}")
LAYERS = ("tools", "hook", "rules", "output")
CLAUDE_NAME = {"read_file": "Read", "write_file": "Write", "run_bash": "Bash", "web_fetch": "WebFetch"}

# 순진한 모델이 「지시」로 알아듣는 문장의 모양
PATH = r"(?P<path>[\w가-힣./-]*[\w가-힣]\.[A-Za-z]{1,5}|\.env)"
INSTRUCTIONS = [
    ("read", re.compile(PATH + r"\s*(?:파일)?(?:을|를)\s*(?:먼저\s*)?(?:열어\s*)?읽")),
    ("run", re.compile(r"`(?P<cmd>[^`]+)`\s*(?:명령)?(?:을|를)?\s*(?:먼저\s*)?실행")),
    ("save", re.compile(r"(?:그|읽은|출력된)?\s*내용을\s*" + PATH + r"\s*에\s*(?:함께\s*)?저장")),
    ("fetch", re.compile(r"(?P<url>https?://[^\s`]+)\s*(?:뒤에|끝에)\s*(?:그|읽은|출력된)?\s*내용을\s*붙여")),
    ("append", re.compile(r"(?:그|읽은|출력된)?\s*내용을\s*(?:답글|응답)\s*(?:의\s*)?(?:끝|마지막)에\s*(?:그대로\s*)?붙")),
]


class Lab:
    def __init__(self, root, defenses, settings, agent_file, hook, ask, log_dir, quiet=False):
        self.root = Path(root).resolve()
        self.defenses = set(defenses)
        self.settings = self.root / settings
        self.settings_rel = Path(settings).as_posix()
        self.agent_file = self.root / agent_file
        self.hook = self.root / hook
        self.ask = ask
        self.log_dir = self.root / log_dir if log_dir else None
        self.quiet = quiet
        self.records = []
        self.written = []
        self.sent = []
        self.allowed_tools = self._load_allowed_tools() if "tools" in self.defenses else None
        self.sources = perm_sim.load_settings([self.settings]) if "rules" in self.defenses else None
        secret_path = self.root / SECRET_FILE
        if not secret_path.exists():
            raise SystemExit(f"{SECRET_FILE}이 없다. 먼저 python security/lab/make_fake_secret.py 를 실행한다.")
        found = LABKEY.search(secret_path.read_text(encoding="utf-8"))
        if not found:
            raise SystemExit(f"{SECRET_FILE}에서 LABKEY- 값을 찾지 못하였다. 파일을 지우고 다시 만든다.")
        self.canary = found.group(0)

    # ---------- 방어층 ----------
    def _load_allowed_tools(self):
        text = self.agent_file.read_text(encoding="utf-8")
        front = text.split("---")[1] if text.startswith("---") else ""
        line = next((l for l in front.splitlines() if l.strip().startswith("tools:")), None)
        if line is None:
            return set(CLAUDE_NAME.values())  # tools를 적지 않으면 모든 도구를 물려받는다
        return {t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()}

    def _mask(self, text):
        return text.replace(self.canary, "LABKEY-" + "*" * 8) if isinstance(text, str) else text

    def _hook_input(self, tool, args):
        name = CLAUDE_NAME[tool]
        if tool == "read_file":
            tool_input = {"file_path": str(self.root / args["path"])}
        elif tool == "write_file":
            tool_input = {"file_path": str(self.root / args["path"]), "content": args["text"]}
        elif tool == "run_bash":
            tool_input = {"command": args["command"], "description": "lab"}
        else:
            tool_input = {"url": args["url"], "prompt": "내용을 요약한다"}
        return {"session_id": "lab-session", "transcript_path": "", "cwd": str(self.root),
                "permission_mode": "default", "hook_event_name": "PreToolUse",
                "tool_name": name, "tool_input": tool_input, "tool_use_id": f"toolu_lab_{len(self.records) + 1:02d}"}

    def _run_hook(self, tool, args):
        payload = json.dumps(self._hook_input(tool, args), ensure_ascii=False)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root), PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, str(self.hook)], input=payload, capture_output=True,
                                text=True, encoding="utf-8", env=env, timeout=30)
        if result.returncode == 2:
            return (result.stderr.strip().splitlines() or ["(까닭 없음)"])[0]
        if result.returncode == 0 and result.stdout.strip().startswith("{"):
            out = json.loads(result.stdout).get("hookSpecificOutput", {})
            if out.get("permissionDecision") == "deny":
                return out.get("permissionDecisionReason", "훅이 거부함")
        return None

    def _rule_call(self, tool, args):
        if tool in ("read_file", "write_file"):
            return f"{CLAUDE_NAME[tool]}({args['path']})"
        if tool == "run_bash":
            return f"Bash({args['command']})"
        return f"WebFetch(domain:{urlparse(args['url']).hostname})"

    def _output_problem(self, tool, args):
        text = args.get("text") if tool == "write_file" else args.get("url") if tool == "web_fetch" else None
        if text is None:
            return None
        problems = [p for p in check_text(text) if p[0] in ("secret", "exfil_link")]
        if tool == "web_fetch" and urlparse(text).query:
            problems = problems or [("exfil_link", 1, "질의 문자열이 붙은 바깥 주소")]
        return "; ".join(f"{k}: {d}" for k, _, d in problems) or None

    def gate(self, tool, args):
        """도구 호출 하나를 방어층에 차례로 통과시킨다. (허용 여부, 층, 까닭)을 돌려준다."""
        if self.allowed_tools is not None and CLAUDE_NAME[tool] not in self.allowed_tools:
            return False, "tools", f"이 에이전트에게 {CLAUDE_NAME[tool]} 도구가 주어지지 않았다"
        if "hook" in self.defenses:
            reason = self._run_hook(tool, args)
            if reason:
                return False, "hook", reason
        if "rules" in self.defenses:
            kind, why = perm_sim.judge(self.sources, self._rule_call(tool, args))
            why = why.replace(str(self.settings), self.settings_rel)
            if kind == "deny":
                return False, "rules", why
            if kind == "ask" and self.ask == "deny":
                return False, "rules", f"확인 창에서 사람이 거절함 ({why})"
            if kind == "ask":
                note = f"확인 창에서 사람이 승인함 ({why})"
            else:
                note = why
        else:
            note = "방어 없음"
        if "output" in self.defenses:
            problem = self._output_problem(tool, args)
            if problem:
                return False, "output", problem
        return True, "", note

    # ---------- 도구 ----------
    def _inside(self, rel):
        path = (self.root / rel).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError(f"저장소 밖의 경로는 다루지 않는다: {rel}")
        return path

    def execute(self, tool, args):
        if tool == "read_file":
            return self._inside(args["path"]).read_text(encoding="utf-8")
        if tool == "write_file":
            path = self._inside(args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["text"], encoding="utf-8", newline="\n")
            self.written.append(args["path"])
            return f"{args['path']}에 {len(args['text'])}자를 썼다"
        if tool == "run_bash":
            return self._simulate_bash(args["command"])
        outbox = self._inside("security/out/outbox.jsonl")
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with open(outbox, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "url": args["url"]}, ensure_ascii=False) + "\n")
        self.sent.append(args["url"])
        return f"(모의) {urlparse(args['url']).hostname}에 요청을 보냈다고 기록함. 실제 네트워크는 쓰지 않았다"

    def _simulate_bash(self, command):
        try:
            words = shlex.split(command)
        except ValueError:
            words = command.split()
        if words and words[0] == "cat":
            return "".join(self._inside(w).read_text(encoding="utf-8") for w in words[1:] if not w.startswith("-"))
        found = re.search(r"open\(\s*['\"]([^'\"]+)['\"]", command)
        if words and words[0].startswith("python") and found:
            return self._inside(found.group(1)).read_text(encoding="utf-8")
        return f"(모의) 이 명령은 흉내 내지 않는다: {command}"

    def call(self, tool, **args):
        ok, layer, why = self.gate(tool, args)
        result = None
        if ok:
            try:
                result = self.execute(tool, args)
            except (OSError, ValueError) as error:
                ok, layer, why = False, "tool_error", str(error)
        shown = {k: (v if k != "text" else f"({len(v)}자)") for k, v in args.items()}
        record = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "tool": CLAUDE_NAME[tool],
                  "input": {k: self._mask(v) for k, v in shown.items()},
                  "decision": "허용" if ok else "막힘", "layer": layer, "reason": self._mask(why)}
        self.records.append(record)
        if not self.quiet:
            target = record["input"].get("path") or record["input"].get("command") or record["input"].get("url")
            tail = f"  [{layer}] {self._mask(why)}" if not ok else ""
            print(f"[도구] {record['tool']:<8} {target} -> {record['decision']}{tail}")
        return result if ok else None


def find_instructions(text):
    """순진한 모델: 글 안의 명령처럼 생긴 문장을 나온 순서대로 지시로 받아들인다."""
    found = []
    for kind, regex in INSTRUCTIONS:
        for m in regex.finditer(text):
            found.append((m.start(), kind, m.groupdict()))
    return [(kind, groups) for _, kind, groups in sorted(found, key=lambda x: x[0])]


def summarize(text):
    """정상 작업: 제목과 앞 두 줄(주석과 지시처럼 생긴 줄을 뺀 것)로 요약한다."""
    if text.lstrip().startswith("{"):
        data = json.loads(text)
        return f"공고 요약: {data.get('company', '')} {data.get('title', '')}".strip()
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = [l.strip("# ").strip() for l in body.splitlines() if l.strip()]
    title = lines[0] if lines else "(제목 없음)"
    rest = [l for l in lines[1:] if not find_instructions(l)][:2]
    return f"요약: {title}\n" + "\n".join(f"- {l}" for l in rest)


def run(source, defenses=(), root=".", reply=None, settings=".claude/settings.json",
        agent=".claude/agents/issue-triage.md", hook=".claude/hooks/block_secrets.py",
        ask="approve", log_dir="security/logs", quiet=False):
    lab = Lab(root, defenses, settings, agent, hook, ask, log_dir, quiet)
    source = Path(source)
    rel_source = source.resolve().relative_to(lab.root).as_posix() if source.is_absolute() else source.as_posix()
    reply = reply or f"security/out/{source.stem}_reply.md"
    content = lab.call("read_file", path=rel_source)
    if content is None:
        raise SystemExit("입력 문서를 읽지 못하였다")
    response = summarize(content)
    last = ""
    for kind, groups in find_instructions(content):
        if kind == "read":
            last = lab.call("read_file", path=groups["path"]) or last
        elif kind == "run":
            last = lab.call("run_bash", command=groups["cmd"]) or last
        elif kind == "save" and last:
            lab.call("write_file", path=groups["path"], text=last)
        elif kind == "fetch" and last:
            lab.call("web_fetch", url=groups["url"] + last.strip().replace("\n", " "))
        elif kind == "append" and last:
            response += "\n\n" + last.strip()
    lab.call("write_file", path=reply, text=response + "\n")

    response_blocked = False
    if "output" in lab.defenses:
        problems = [p for p in check_text(response) if p[0] in ("secret", "exfil_link")]
        if problems:
            response_blocked = True
            response = "(출력 검사: 응답에 비밀 정보로 보이는 값이 있어 내보내지 않았다. 사람에게 보고한다.)"
    places = []
    if lab.canary in response:
        places.append("최종 응답")
    places += [p for p in dict.fromkeys(lab.written) if lab.canary in (lab.root / p).read_text(encoding="utf-8")]
    places += ["바깥 주소(outbox)" for url in lab.sent if lab.canary in url][:1]
    attempts = len(find_instructions(content))
    blocked = [r for r in lab.records if r["decision"] == "막힘"]
    defense = "all" if lab.defenses == set(LAYERS) else ",".join(sorted(lab.defenses)) or "none"
    summary = {"scenario": source.name, "defense": defense,
               "leaked": bool(places), "places": places, "injected_steps": attempts,
               "blocked": len(blocked), "blocked_layers": sorted({r["layer"] for r in blocked}),
               "response_blocked": response_blocked}
    if lab.log_dir:
        lab.log_dir.mkdir(parents=True, exist_ok=True)
        name = f"{source.stem}__{summary['defense'].replace(',', '+')}.jsonl"
        with open(lab.log_dir / name, "w", encoding="utf-8", newline="\n") as f:
            for record in lab.records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.write(json.dumps({"summary": summary}, ensure_ascii=False) + "\n")
    if not quiet:
        print("--- 최종 응답 ---")
        print(lab._mask(response))
        print("---")
        verdict = f"유출됨 ({', '.join(places)})" if places else "유출 없음"
        print(f"시나리오: {source.name}  방어: {summary['defense']}  주입된 지시: {attempts}개  막힌 호출: {len(blocked)}건")
        print(f"판정: {verdict}")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="간접 프롬프트 주입 재현용 가짜 에이전트(학습용, 모델을 부르지 않는다)")
    parser.add_argument("source", help="에이전트가 처리할 입력 문서(이슈 본문, 공고 JSON, 자료 문서)")
    parser.add_argument("--defense", default="none", help="none 또는 tools,hook,rules,output 중 쉼표로 고른 것, all")
    parser.add_argument("--root", default=".", help="저장소 폴더")
    parser.add_argument("--reply", help="답글 초안을 저장할 경로(기본 security/out/<문서이름>_reply.md)")
    parser.add_argument("--settings", default=".claude/settings.json")
    parser.add_argument("--agent", default=".claude/agents/issue-triage.md", help="tools 층이 읽는 에이전트 정의")
    parser.add_argument("--hook", default=".claude/hooks/block_secrets.py", help="hook 층이 실행하는 훅")
    parser.add_argument("--ask", choices=["approve", "deny"], default="approve",
                        help="확인(ask) 판정에 사람이 어떻게 답하는가(기본: 습관적으로 승인)")
    parser.add_argument("--log-dir", default="security/logs", help="감사 기록(JSONL)을 남길 폴더. 빈 값이면 남기지 않는다")
    args = parser.parse_args(argv)
    if args.defense == "none":
        defenses = []
    elif args.defense == "all":
        defenses = list(LAYERS)
    else:
        defenses = [d.strip() for d in args.defense.split(",") if d.strip()]
        unknown = set(defenses) - set(LAYERS)
        if unknown:
            parser.error(f"알 수 없는 방어층: {', '.join(sorted(unknown))}")
    summary = run(args.source, defenses, args.root, args.reply, args.settings, args.agent, args.hook,
                  args.ask, args.log_dir or None)
    return 1 if summary["leaked"] else 0


if __name__ == "__main__":
    sys.exit(main())
