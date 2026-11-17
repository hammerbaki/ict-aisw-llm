"""Claude Code 설정(.claude/settings.json)의 권한 규칙과 훅이 에이전트 루프의 어디에 끼는지 보여 준다.

사용법(저장소 폴더에서)
    python ~/kits/Agent_09장/도구/loop_map.py .claude/settings.json [.claude/agents]

출력은 루프의 단계 순서(① 입력 → ② 모델 호출 → ③ 도구 실행 → ④ 결과 → ⑤ 종료)로 정렬된다.
표준 라이브러리만 쓴다. 설정을 바꾸지 않고 읽기만 한다.
"""

import json
import sys
from pathlib import Path

# 훅 이벤트 → (단계 번호, 단계 이름, 이 과목의 루프 loop.py에서 대응하는 곳)
STAGES = {
    "SessionStart":       ("0", "세션 시작", "run_agent() 호출 전"),
    "UserPromptSubmit":   ("①", "사용자 입력", "messages = [{'role': 'user', ...}]"),
    "PreToolUse":         ("③a", "도구 실행 직전", "execute()의 pre_tool_hooks"),
    "PermissionRequest":  ("③b", "권한 확인(물어야 할 때)", "execute()의 approver"),
    "PostToolUse":        ("③c", "도구 실행 직후(성공)", "run_tool() 뒤"),
    "PostToolUseFailure": ("③c", "도구 실행 직후(실패)", "run_tool()이 is_error를 낸 뒤"),
    "SubagentStart":      ("③d", "서브에이전트 시작(Agent 도구 실행)", "도구 하나의 처리 함수 안에서 run_agent()를 새로"),
    "SubagentStop":       ("③d", "서브에이전트 종료", "그 run_agent()의 반환"),
    "PreCompact":         ("②", "대화 기록 압축 직전", "messages가 커질 때(이 과목의 루프에는 없음)"),
    "Stop":               ("⑤", "응답 종료(end_turn)", "stop == 'end_turn'에서 return 직전"),
    "SessionEnd":         ("⑥", "세션 종료", "run_agent() 반환 뒤"),
}
ORDER = ["0", "①", "②", "③", "③a", "③b", "③c", "③d", "⑤", "⑥"]


def main(argv):
    for stream in (sys.stdout, sys.stderr):   # Windows에서 파이프로 넘겨도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")
    if len(argv) < 2:
        print(__doc__)
        return 1
    settings_path = Path(argv[1])
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    rows = []

    for event, groups in settings.get("hooks", {}).items():
        stage, title, ours = STAGES.get(event, ("?", event, "-"))
        for group in groups:
            matcher = group.get("matcher", "*") or "*"
            for hook in group.get("hooks", []):
                what = hook.get("command") or hook.get("prompt") or hook.get("type")
                rows.append((stage, f"훅 {event} [{matcher}]", title, what, ours))

    permissions = settings.get("permissions", {})
    for kind, label in (("deny", "거부 규칙"), ("ask", "묻기 규칙"), ("allow", "허용 규칙")):
        rules = permissions.get(kind, [])
        if rules:
            shown = ", ".join(rules[:3]) + (f" 외 {len(rules) - 3}개" if len(rules) > 3 else "")
            rows.append(("③b", f"{label} {len(rules)}개", "권한 판정", shown, "execute()의 needs_approval/approver"))
    if "defaultMode" in permissions:
        rows.append(("③b", f"권한 모드 {permissions['defaultMode']}", "권한 판정", "mode", "-"))

    if len(argv) > 2:
        for path in sorted(Path(argv[2]).glob("*.md")):
            rows.append(("③d", f"서브에이전트 {path.stem}", "Agent 도구로 실행", path.name,
                         "도구 하나 = 별도의 run_agent()(새 messages, 요약만 돌려줌)"))

    rows.sort(key=lambda row: ORDER.index(row[0]) if row[0] in ORDER else len(ORDER))
    print(f"설정: {settings_path}")
    for stage, name, title, what, ours in rows:
        print(f"{stage:<3} {title} | {name} | {what}")
        print(f"    → loop.py: {ours}")
    print(f"항목 {len(rows)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
