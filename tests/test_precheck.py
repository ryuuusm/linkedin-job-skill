"""Tests for precheck.py: sensitive data, placeholders, company names, numbers, keywords."""
import precheck


def run(text, **kw):
    kw.setdefault("others", [])
    kw.setdefault("profile_numbers", None)
    kw.setdefault("public", False)
    return precheck.check_text("f.md", text, **kw)


def rules(findings, level=None):
    return [f.rule for f in findings if level is None or f.level == level]


def test_placeholders_are_errors():
    res = run("Hello [미입력] and TODO and {{company}} and [Title]")
    assert rules(res, "ERROR").count("자리표시") == 4


def test_rrn_and_card_detected():
    res = run("900101-1234567\n4111 1111 1111 1111")
    assert "주민등록번호 형태" in rules(res, "ERROR")
    assert "카드번호 형태" in rules(res, "ERROR")


def test_long_non_card_number_not_flagged():
    # 16 digits failing the Luhn check must not be reported as a card.
    assert "카드번호 형태" not in rules(run("1234567890123456"))


def test_other_company_word_boundary():
    res = run("I worked on metadata at Meta", others=["Meta"])
    errs = [f for f in res if f.rule == "다른 회사명"]
    assert len(errs) == 1


def test_korean_company_substring():
    assert "다른 회사명" in rules(run("삼성전자에 지원합니다", others=["삼성전자"]))


def test_cliches_en_and_ko():
    res = run("Passionate, results-driven team player\n열정과 시너지")
    assert rules(res, "WARN").count("상투어") == 5


def test_public_contact_info():
    res = run("mail me: a.b@example.com / 010-1234-5678", public=True)
    assert rules(res, "WARN").count("공개 연락처") == 2
    assert "공개 연락처" not in rules(run("a.b@example.com", public=False))


def test_numbers_not_in_profile_warn():
    profile = precheck.numbers_in("Led 12 projects, cut cost by 30%, since 2019, 1,200 users")
    res = run("Led 12 projects for 1200 users, cut 45% cost", profile_numbers=profile)
    warned = [f.text for f in res if f.rule == "프로필에 없는 숫자"]
    assert len(warned) == 1 and "'45'" in warned[0]


def test_notes_excluded():
    assert run("> TODO internal memo\n<!-- [미입력] -->\nclean") == []


def test_keyword_coverage():
    res = precheck.keyword_coverage(["SAP and python"], ["SAP", "Python", "ITGC"])
    assert "SAP" in res[0].text and "Python" in res[0].text
    assert "ITGC" in res[1].text


def test_cli_with_tracker_and_target(tmp_path):
    tracker = tmp_path / "t.csv"
    tracker.write_text("company,title\nACME,PM\nGlobex,Analyst\n", encoding="utf-8")
    doc = tmp_path / "a.md"
    doc.write_text("Why ACME: I like ACME's products.", encoding="utf-8")
    assert precheck.main([str(doc), "--tracker", str(tracker), "--target", "ACME"]) == 0
    doc.write_text("Why Globex: ...", encoding="utf-8")
    assert precheck.main([str(doc), "--tracker", str(tracker), "--target", "ACME"]) == 1


def test_cli_bad_tracker_header(tmp_path):
    tracker = tmp_path / "t.csv"
    tracker.write_text("name,title\nACME,PM\n", encoding="utf-8")
    doc = tmp_path / "a.md"
    doc.write_text("x", encoding="utf-8")
    assert precheck.main([str(doc), "--tracker", str(tracker)]) == 2
