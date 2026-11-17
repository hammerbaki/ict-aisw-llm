from datetime import date
from pathlib import Path

from deadline import load_applications, render

CSV = Path(__file__).resolve().parents[1] / "applications.csv"


def test_load_reads_four_rows():
    apps = load_applications(CSV)
    assert len(apps) == 4
    assert apps[0]["company"] == "한빛데이터"
    assert apps[0]["deadline"] == date(2027, 3, 20)


def test_render_keeps_csv_order():
    lines = render(load_applications(CSV), date(2027, 3, 10))
    companies = ["한빛데이터", "가람소프트", "누리시스템", "다온랩"]
    assert len(lines) == len(companies)
    for line, company in zip(lines, companies):
        assert company in line
