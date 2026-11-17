"""도구들이 함께 쓰는 함수. 직접 실행하지 않는다."""
from __future__ import annotations

import importlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def fill(value, inputs: dict):
    """양식 값의 {이름} 자리를 inputs로 채운다. 값 전체가 "{limit}"처럼 자리 하나면 원래 형(정수 등)을 살린다."""
    if isinstance(value, str):
        if value.startswith("{") and value.endswith("}") and value[1:-1] in inputs:
            return inputs[value[1:-1]]
        out = value
        for k, v in inputs.items():
            out = out.replace("{" + k + "}", str(v))
        return out
    if isinstance(value, list):
        return [fill(v, inputs) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, inputs) for k, v in value.items()}
    return value


class Client:
    """--base(실행 중인 서버) 또는 --app-dir(같은 프로세스 안의 FastAPI 앱)로 요청을 보낸다."""

    def __init__(self, base: str | None = None, app_dir: str | None = None):
        self.base = base.rstrip("/") if base else None
        self.tc = None
        if app_dir:
            os.environ.setdefault("LLM_FAKE", "1")
            sys.path.insert(0, str(Path(app_dir).resolve()))
            from fastapi.testclient import TestClient

            # 백엔드 앱은 10장에서 정한 jobprep/api/app.py의 app이다(정합 기준 4절)
            module = importlib.import_module("api.app")
            self.tc = TestClient(module.app)
        if not self.base and not self.tc:
            raise SystemExit("--base 또는 --app-dir 중 하나를 준다.")

    def post(self, path: str, body: dict) -> tuple[int, dict, float]:
        start = time.perf_counter()
        if self.tc:
            r = self.tc.post(path, json=body)
            status, text = r.status_code, r.text
        else:
            req = urllib.request.Request(
                self.base + path,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    status, text = resp.status, resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                status, text = e.code, e.read().decode("utf-8")
        ms = (time.perf_counter() - start) * 1000
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"_raw": text}
        return status, data, ms


def read_tables(path: str | Path) -> list[tuple[list[str], list[list[str]]]]:
    """마크다운 파일의 표를 (머리글, 행 목록)으로 돌려준다."""
    tables, header, rows = [], None, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if header is None:
                header = cells
            elif all(set(c) <= set("-: ") for c in cells):
                continue
            else:
                rows.append(cells)
        else:
            if header is not None:
                tables.append((header, rows))
            header, rows = None, []
    if header is not None:
        tables.append((header, rows))
    return tables
