import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_pii  # noqa: E402


def kinds(items):
    return [kind for _, kind, _ in items]


def test_phone_email_rrn_fail():
    text = "L1 A: 연락은 010-1234-5678로\nL2 A: 메일은 someone@example.com\nL3 A: 900101-1234567\n"
    fails, _ = check_pii.scan_text(text)
    assert kinds(fails) == ["전화번호", "이메일", "주민등록번호 형식"]


def test_phone_without_dashes():
    fails, _ = check_pii.scan_text("L1 A: 01012345678")
    assert kinds(fails) == ["전화번호"]


def test_names_from_list_fail():
    fails, _ = check_pii.scan_text("L4 A: 홍길동 선배가 알려 줬다", names=["홍길동"])
    assert kinds(fails) == ["이름 목록의 이름"]


def test_warnings_for_student_id_school_sns():
    text = "L1 A: 학번은 2026123456\nL2 A: 한빛대학교 친구\nL3 A: 인스타 @job_ready_kim\n"
    fails, warns = check_pii.scan_text(text)
    assert fails == []
    assert kinds(warns) == ["학번으로 보이는 숫자", "학교 이름", "SNS 아이디"]


def test_email_is_not_double_reported_as_sns():
    _, warns = check_pii.scan_text("L2 A: a.b@example.com")
    assert "SNS 아이디" not in kinds(warns)


def test_generic_words_are_clean():
    text = ("L1 A: 전문대학 2학년이다.\nL2 A: 4년제 대학 출신과 경쟁한다.\nL3 A: 진로 3년 차 고민이다.\n"
            "L4 A: 공고 마감은 2027-04-30이다.\n")
    fails, warns = check_pii.scan_text(text)
    assert fails == [] and warns == []


def test_address_warning():
    _, warns = check_pii.scan_text("L1 A: 집은 성남시 중원구 둔촌대로 123 근처")
    assert "상세 주소" in kinds(warns)


def test_main_exit_codes(tmp_path, capsys):
    d = tmp_path / "기록"
    d.mkdir()
    (d / "인터뷰_01.md").write_text("## 기록\n\nL1 A: 깨끗한 기록\n", encoding="utf-8")
    assert check_pii.main([str(d)]) == 0
    (d / "인터뷰_02.md").write_text("## 기록\n\nL1 A: 010 9876 5432\n", encoding="utf-8")
    assert check_pii.main([str(d)]) == 1
    names = tmp_path / "names.txt"
    names.write_text("김하늘\n", encoding="utf-8")
    (d / "인터뷰_02.md").write_text("## 기록\n\nL1 A: 김하늘이 말했다\n", encoding="utf-8")
    assert check_pii.main([str(d), "--names", str(names)]) == 1
    assert "이름 목록의 이름 '김하늘'" in capsys.readouterr().out
