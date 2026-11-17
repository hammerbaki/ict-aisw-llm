"""프롬프트 판본 파일(prompts/vN.md)을 읽는다.

파일 형식
    ---
    판본: v2
    바꾼 점: (한 줄)
    ---
    ## system
    (시스템 프롬프트)
    ## user
    (사용자 메시지 틀. {공고} 자리에 공고 본문이 들어간다)

틀 채우기는 str.format이 아니라 replace를 쓴다. 프롬프트 안의 JSON 예시에 중괄호가 있기 때문이다.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
PLACEHOLDER = "{공고}"


@dataclass
class Prompt:
    version: str
    note: str
    system: str
    user_template: str
    sha256: str

    def render(self, posting: str) -> str:
        return self.user_template.replace(PLACEHOLDER, posting.strip())


def load_prompt(version: str, prompt_dir: Path = PROMPT_DIR) -> Prompt:
    path = Path(prompt_dir) / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"프롬프트 파일이 없다: {path}")
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, head, body = raw.split("---", 2)
        for line in head.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    parts: dict[str, list[str]] = {"system": [], "user": []}
    current = None
    for line in body.splitlines():
        if line.strip().lower() in ("## system", "## user"):
            current = line.strip().lower()[3:]
            continue
        if current:
            parts[current].append(line)
    system = "\n".join(parts["system"]).strip()
    user = "\n".join(parts["user"]).strip()
    if not system or PLACEHOLDER not in user:
        raise ValueError(f"{path.name}: '## system'과 '{PLACEHOLDER}'가 든 '## user'가 모두 있어야 한다")
    return Prompt(
        version=meta.get("판본", version),
        note=meta.get("바꾼 점", ""),
        system=system,
        user_template=user,
        sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )
