"""두 변형에 같은 시험지를 낸다: 자기소개서 피드백의 공통 자동 검사 5개.

변형마다 API 모양이 다르므로, 요청을 어떻게 보내고 응답의 어디를 볼지는 검사 어댑터(JSON)가 정한다.
검사는 모의 모드(LLM_FAKE=1)에서 같은 프로세스 안의 앱으로 돈다. 서버를 띄우지 않아도 된다.

    python 도구/check_common.py --app-dir ~/llm-service-lab/jobprep --adapter 검사어댑터/form.json

끝 상태 코드: 모두 통과 0, 하나라도 실패 1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Client, fill, utf8_stdout  # noqa: E402

MARK = "ZQX표지문장"
NORMAL = (
    f"저는 학과 팀 과제에서 일정 관리를 맡았습니다. {MARK} 공유 문서에 할 일과 마감을 정리하고 매주 진행 상황을 "
    "점검하여, 두 번 있던 마감 지연을 다음 과제에서는 한 번도 내지 않았습니다. 입사 후에도 업무 일정을 "
    "문서로 공유하는 습관으로 팀의 일정을 지키는 데 기여하겠습니다."
)
SHORT = "열심히 하겠습니다."
QUESTION = "지원 동기와 입사 후 포부를 쓰시오."


def body_for(adapter: dict, answer: str, limit: int) -> dict:
    return fill(adapter["body"], {"question": QUESTION, "answer": answer, "limit": limit})


def get(data: dict, field: str):
    return data.get(field) if isinstance(data, dict) else None


def has_parts(adapter: dict, data: dict) -> bool:
    parts = adapter["parts"]
    if parts["mode"] == "fields":
        values = [get(data, f) for f in parts["fields"]]
        return all(values) and all(len(v) >= 2 for v in values[:2] if isinstance(v, list))
    text = str(get(data, parts["field"]) or "")
    return all(m in text for m in parts["markers"])


def shows_over(adapter: dict, data: dict) -> bool:
    rule = adapter["over_limit"]
    if rule["mode"] == "field":
        return get(data, rule["field"]) is True
    return rule["contains"] in str(get(data, rule["field"]) or "")


def count_calls(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8")) if path.exists() else 0


def main() -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--app-dir", required=True, help="jobprep 폴더(api/app.py가 있는 곳)")
    ap.add_argument("--adapter", required=True, help="검사 어댑터 JSON")
    args = ap.parse_args()

    adapter = json.loads(Path(args.adapter).read_text(encoding="utf-8"))
    log = Path(tempfile.mkdtemp()) / "check_calls.jsonl"
    os.environ.update({"LLM_FAKE": "1", "LLM_LOG_PATH": str(log), "JOBPREP_VARIANT": adapter["variant"]})
    os.environ.pop("LLM_FAKE_FAIL", None)
    os.environ.pop("LLM_FAKE_LATENCY", None)
    started = time.time()
    client = Client(app_dir=args.app_dir)
    path = adapter["path"]
    results = []

    status, data, _ = client.post(path, body_for(adapter, NORMAL, 700))
    if status in (404, 405):
        print(f"공통 검사: {adapter['variant']} ({path})")
        print(f"  경로 {path}가 없다(HTTP {status}). 변형을 구현한 브랜치에서 실행한다.")
        print("통과 0/5")
        return 1
    results.append(("REQ-081", "피드백 세 부분(강점, 보완점, 예시)", status == 200 and has_parts(adapter, data)))

    status, data, _ = client.post(path, body_for(adapter, NORMAL, 100))
    results.append(("REQ-082", "글자 수 초과 표시", status == 200 and shows_over(adapter, data)))

    before = count_calls(log)
    status, data, _ = client.post(path, body_for(adapter, SHORT, 700))
    results.append(("REQ-083", "짧은 답변은 LLM을 부르지 않음", status < 500 and count_calls(log) == before))

    os.environ["LLM_FAKE_FAIL"] = "1"
    status, data, _ = client.post(path, body_for(adapter, NORMAL, 700))
    os.environ.pop("LLM_FAKE_FAIL")
    results.append(("REQ-086", "호출 실패 시 502·503과 안내", status in (502, 503) and bool(data.get("detail"))))

    leaked = []
    for f in [log, *Path(args.app_dir).rglob("*")]:
        if f.is_file() and f.stat().st_mtime >= started and ".git" not in f.parts and f.suffix not in (".pyc",):
            try:
                if MARK in f.read_text(encoding="utf-8", errors="ignore"):
                    leaked.append(str(f))
            except OSError:
                pass
    results.append(("REQ-087", "답변이 파일·기록에 남지 않음", not leaked))

    print(f"공통 검사: {adapter['variant']} ({path})")
    for rid, name, ok in results:
        print(f"  {rid} {name:<24} {'PASS' if ok else 'FAIL'}")
    for f in leaked:
        print(f"    답변이 남은 파일: {f}")
    passed = sum(ok for *_, ok in results)
    print(f"통과 {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
