"""Tests for li_lint.py: counting, limits, section parsing and config validation."""
import json

import pytest

import li_lint
from _common import InputError


@pytest.fixture
def limits():
    return li_lint.load_limits(None)


def levels(results, section_prefix):
    return [r.level for r in results if r.section.startswith(section_prefix)]


def test_default_limits_load(limits):
    fields, ratio = limits
    keys = {f.key: f.limit for f in fields}
    assert keys == {"headline": 220, "about": 2600, "experience": 2000}
    assert ratio == 0.9


def test_count_chars_korean_and_emoji():
    assert li_lint.count_chars("한국어") == {"chars": 3, "utf16": 3}
    # Emoji outside the BMP take two UTF-16 units.
    assert li_lint.count_chars("🚀") == {"chars": 1, "utf16": 2}
    # Decomposed Hangul (NFD) is normalised before counting.
    import unicodedata
    assert li_lint.count_chars(unicodedata.normalize("NFD", "한"))["chars"] == 1


def test_headline_over_limit_is_error(limits):
    text = "## Headline\n" + "가" * 221 + "\n"
    res = li_lint.lint(text, *limits)
    assert "ERROR" in levels(res, "Headline")


def test_headline_near_limit_is_warn(limits):
    text = "## Headline\n" + "a" * 200 + "\n"   # 200 >= 0.9 * 220
    assert levels(li_lint.lint(text, *limits), "Headline") == ["WARN"]


def test_notes_and_comments_not_counted(limits):
    body = "a" * 219
    text = f"## Headline\n> memo {'x' * 500}\n<!-- {'y' * 500} -->\n{body}\n"
    res = [r for r in li_lint.lint(text, *limits) if r.level in ("ERROR", "OK", "WARN")]
    assert res[0].level == "WARN" and "219자" in res[0].message


def test_experience_sections_checked_individually(limits):
    text = ("## Experience: PM @ A\n" + "x" * 2001 + "\n"
            "## 경력: 개발자 @ B\n짧은 설명\n")
    res = li_lint.lint(text, *limits)
    assert [r.level for r in res if r.level in ("ERROR", "OK")] == ["ERROR", "OK"]


def test_korean_alias_and_markdown_info(limits):
    text = "## 소개\n**굵게** 그리고 [링크](https://example.com)\n"
    res = li_lint.lint(text, *limits)
    assert any(r.level == "INFO" and "굵게" in r.message for r in res)
    assert any(r.level == "INFO" and "링크" in r.message for r in res)


def test_single_line_field_with_newline_warns(limits):
    res = li_lint.lint("## Headline\nline one\nline two\n", *limits)
    assert any(r.level == "WARN" and "줄바꿈" in r.message for r in res)


def test_no_sections_is_error(limits):
    res = li_lint.lint("just text", *limits)
    assert res[0].level == "ERROR"


def test_heading_in_code_fence_ignored(limits):
    text = "## About\n```\n## Headline\n```\nbody\n"
    names = {r.section for r in li_lint.lint(text, *limits)}
    assert names == {"About"}


@pytest.mark.parametrize("bad", [
    {"fields": {"h": {"limit": 0}}},
    {"fields": {"h": {"limit": True}}},
    {"fields": {"h": {"limit": 10, "aliases": "headline"}}},
    {"fields": {"h": {"limit": 10}}, "warn_ratio": 2},
    {"nofields": {}},
])
def test_invalid_limits_rejected(tmp_path, bad):
    p = tmp_path / "limits.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(InputError):
        li_lint.load_limits(str(p))


def test_cli_exit_codes(tmp_path, capsys):
    ok = tmp_path / "ok.md"
    ok.write_text("## Headline\nIT PM | SAP | GxP\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("## Headline\n" + "x" * 300 + "\n", encoding="utf-8")
    assert li_lint.main([str(ok)]) == 0
    assert li_lint.main([str(bad)]) == 1
    assert li_lint.main([str(tmp_path / "missing.md")]) == 2


def test_cli_json_output(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text("## About\nhello\n", encoding="utf-8")
    li_lint.main([str(f), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data[0]["level"] == "OK" and data[0]["section"] == "About"


def test_default_limit_for_answers(limits):
    text = "## Q1: Why us?\n" + "a" * 501 + "\n## Q2: Start date\nImmediately\n"
    res = li_lint.lint(text, *limits, default_limit=500)
    assert [r.level for r in res] == ["ERROR", "OK"]
    # Without --max, unknown sections are only reported as INFO.
    assert {r.level for r in li_lint.lint(text, *limits)} == {"INFO"}


def test_cli_rejects_bad_max(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("## Q1: x\ny\n", encoding="utf-8")
    assert li_lint.main([str(f), "--max", "0"]) == 2


def test_template_parses(limits):
    from pathlib import Path
    tpl = Path(li_lint.__file__).resolve().parent.parent / "templates" / "profile-draft.md"
    res = li_lint.lint(tpl.read_text(encoding="utf-8"), *limits)
    assert not any(r.level == "ERROR" for r in res)
