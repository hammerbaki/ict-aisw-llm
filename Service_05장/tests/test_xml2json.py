"""xml2json.py와 도구/predeploy.py의 테스트. 키트 폴더에서 `python -m pytest -q`로 실행한다."""
import json
import os
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SAMPLE = KIT / "견본/응답_지어낸것.xml"
sys.path.insert(0, str(KIT / "도구"))

import predeploy  # noqa: E402


def convert(src, dst):
    return subprocess.run([sys.executable, str(KIT / "xml2json.py"), str(src), str(dst)],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONUTF8": "1"})


def test_견본을_바꾸면_10건이고_쓰지_않는_항목이_없다(tmp_path):
    out = tmp_path / "jobs.json"
    r = convert(SAMPLE, out)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["count"] == 10 and len(d["jobs"]) == 10
    assert "busino" not in d["jobs"][0] and "basicAddr" not in d["jobs"][0]
    assert "빈 값: {'sal': 1}" in r.stdout
    assert "['채용시까지']" in r.stdout


def test_공고가_없는_응답은_0건(tmp_path):
    src = tmp_path / "오류.xml"
    src.write_text("<result><message>인증키 오류(지어낸 예)</message></result>", encoding="utf-8")
    r = convert(src, tmp_path / "jobs.json")
    assert r.returncode == 0
    assert "공고 0건" in r.stdout


def make_site(tmp_path, jobs_extra=None, extra_files=()):
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / ".git").mkdir()
    (site / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (site / "index.html").write_text('<script src="app.js"></script>', encoding="utf-8")
    (site / "app.js").write_text('fetch("data/jobs.json")', encoding="utf-8")
    job = {"company": "가나다소프트", "title": "웹 개발자"}
    job.update(jobs_extra or {})
    (site / "data" / "jobs.json").write_text(json.dumps({"jobs": [job]}, ensure_ascii=False), encoding="utf-8")
    for name, text in extra_files:
        (site / name).write_text(text, encoding="utf-8")
    return site


def test_점검_통과(tmp_path, capsys):
    assert predeploy.main([str(make_site(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "PREDEPLOY_OK 3 files" in out
    assert "data/jobs.json의 항목: company, title" in out


def test_쓰지_않는_항목이_있으면_멈춘다(tmp_path, capsys):
    assert predeploy.main([str(make_site(tmp_path, {"busino": "0000000000"}))]) == 1
    assert "busino" in capsys.readouterr().out


def test_인증키가_있으면_멈춘다(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WORK24_KEY", "FAKE-KEY-0000-1111")
    site = make_site(tmp_path, extra_files=[("note.txt", "FAKE-KEY-0000-1111")])
    assert predeploy.main([str(site)]) == 1
    assert "WORK24_KEY의 값" in capsys.readouterr().out


def test_웹이_아닌_파일과_절대_경로(tmp_path, capsys):
    site = make_site(tmp_path, extra_files=[("응답_견본.xml", "<x/>")])
    (site / "app.js").write_text('fetch("/data/jobs.json")', encoding="utf-8")
    assert predeploy.main([str(site)]) == 1
    out = capsys.readouterr().out
    assert "웹에 쓰지 않는 파일" in out and "/ 로 시작하는 경로" in out


def test_서버확인_자료는_지어낸_견본이다():
    d = json.loads((KIT / "서버확인/data/jobs.json").read_text(encoding="utf-8"))
    assert d["count"] == 10 and d["source"].startswith("지어낸 견본")
    assert predeploy.main([str(KIT / "서버확인")]) == 0
