"""비밀 정보의 모양(패턴)을 한곳에 모은 모듈이다. scan_secrets.py와 check_output.py가 함께 쓴다.

패턴은 공개된 키 형식의 앞부분(접두어)과 길이를 본뜬 것이다. 실제 서비스의 검사기(GitHub 비밀 스캔 등)는
더 많은 형식을 알고, 찾은 키가 지금도 유효한지까지 확인한다. 이 모듈은 수업용으로 줄인 목록이다.

- 실제 키 형식(anthropic, github, aws, private_key)은 테스트에서 문자열을 이어 붙여 실행 중에만 만든다.
  파일에 그대로 적으면 그 파일을 GitHub에 올릴 때 푸시 보호에 걸리기 때문이다.
- lab_key는 이 장의 실습용 가짜 키(LABKEY-로 시작하는 32자리 16진수)이다. 실제 서비스의 키가 아니다.
"""

import math
import re

PATTERNS = [
    # (종류, 정규식, 설명)
    ("anthropic_api_key", re.compile(r"sk-ant-[a-z]{3,5}\d{2}-[A-Za-z0-9_\-]{20,}"), "Anthropic API 키 형식"),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})"), "GitHub 토큰 형식"),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS 액세스 키 ID 형식"),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "개인 키 머리글"),
    ("lab_key", re.compile(r"LABKEY-[0-9a-f]{32}"), "11장 실습용 가짜 키"),
]

# 이름이 비밀처럼 생긴 변수에 긴 값을 넣는 줄. 값이 무작위에 가까울 때(엔트로피가 높을 때)만 잡는다.
ASSIGNMENT = re.compile(
    r"(?i)\b(?P<name>[A-Z0-9_]*(?:API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD)[A-Z0-9_]*)\s*[:=]\s*['\"]?(?P<value>[A-Za-z0-9_\-+/=]{16,})"
)
PLACEHOLDER = re.compile(r"(?i)(example|sample|dummy|changeme|your|xxxx|placeholder|여기에)")
ALLOW_MARK = "secret-scan: allow"  # 이 표시가 있는 줄은 검사하지 않는다(정당한 예외만)


def entropy(text):
    """글자 분포의 섀넌 엔트로피(글자당 비트). 무작위 키는 높고, 사람이 지은 낱말은 낮다."""
    if not text:
        return 0.0
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def mask(value):
    """값의 앞 8자만 남기고 가린다. 보고서와 기록에 비밀이 다시 새지 않게 한다."""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:8] + "*" * 6


def find_secrets(text):
    """text에서 비밀처럼 보이는 것을 찾아 (줄 번호, 종류, 가린 값) 목록을 돌려준다."""
    found = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARK in line:
            continue
        hit_on_line = False
        for kind, regex, _ in PATTERNS:
            for m in regex.finditer(line):
                found.append((lineno, kind, mask(m.group(0))))
                hit_on_line = True
        if hit_on_line:
            continue
        for m in ASSIGNMENT.finditer(line):
            value = m.group("value")
            if PLACEHOLDER.search(value) or entropy(value) < 3.5:
                continue
            found.append((lineno, "generic_assignment", f"{m.group('name')}={mask(value)}"))
    return found


def contains_secret(text):
    return bool(find_secrets(text))
