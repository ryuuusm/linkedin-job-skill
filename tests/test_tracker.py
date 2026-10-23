"""Tests for tracker.py: validation, CSV injection protection and follow-up flags."""
import csv

import tracker


def add(path, *extra):
    return tracker.main(["add", str(path), "--company", "ACME", "--title", "IT PM", *extra])


def test_add_creates_file_with_header(tmp_path):
    p = tmp_path / "apps" / "tracker.csv"
    assert add(p, "--status", "지원완료", "--applied-on", "2026-10-01") == 0
    rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    assert rows[0]["company"] == "ACME" and rows[0]["status"] == "지원완료"
    assert add(p) == 0
    assert len(list(csv.DictReader(p.open(encoding="utf-8-sig")))) == 2


def test_csv_injection_neutralised(tmp_path):
    p = tmp_path / "t.csv"
    assert tracker.main(["add", str(p), "--company", "=HYPERLINK(\"http://evil\")", "--title", "+cmd"]) == 0
    row = next(csv.DictReader(p.open(encoding="utf-8-sig")))
    assert row["company"].startswith("'=") and row["title"].startswith("'+")


def test_rejects_bad_inputs(tmp_path):
    p = tmp_path / "t.csv"
    assert add(p, "--url", "javascript:alert(1)") == 2
    assert add(p, "--applied-on", "2026/10/01") == 2
    assert add(p, "--status", "unknown") == 2
    assert not p.exists()


def test_rejects_foreign_header(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("회사,직무\n", encoding="utf-8")
    assert add(p) == 2


def test_list_flags(tmp_path, capsys):
    p = tmp_path / "t.csv"
    add(p, "--status", "지원완료", "--applied-on", "2026-10-01")
    tracker.main(["add", str(p), "--company", "Globex", "--title", "BA", "--status", "면접",
                  "--next", "2026-10-20"])
    tracker.main(["add", str(p), "--company", "Initech", "--title", "Dev", "--status", "불합격"])
    capsys.readouterr()
    assert tracker.main(["list", str(p), "--today", "2026-10-23"]) == 0
    out = capsys.readouterr().out
    assert "할 일 3일 지남" in out
    assert "지원 22일 경과" in out
    assert "Initech" not in out
