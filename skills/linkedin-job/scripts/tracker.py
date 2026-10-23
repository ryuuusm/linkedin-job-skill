#!/usr/bin/env python3
"""LinkedIn 지원 현황 기록·조회 (표준 라이브러리만 사용).

사용법:
    python tracker.py add applications/tracker.csv --company "ACME" --title "IT PM" \
        --url https://www.linkedin.com/jobs/view/123 --source "Easy Apply" --status 지원완료 \
        [--applied-on 2026-10-23] [--next 2026-11-06] [--contact "채용담당 이름"] [--notes "..."]
    python tracker.py list applications/tracker.csv [--stale-days 14] [--today 2026-10-23]

- add: 입력값을 검증하고(날짜 YYYY-MM-DD, URL은 http/https만, 상태는 정해진 값만) 한 줄 추가한다.
       파일이 없으면 헤더(templates/tracker.csv와 동일)를 만들어 준다.
       엑셀에서 열 때 수식으로 실행되지 않도록 =,+,-,@ 로 시작하는 값 앞에 ' 를 붙인다(CSV 인젝션 방지).
- list: 진행 중인 지원을 다음 할 일 날짜순으로 보여주고,
        지원 후 --stale-days 동안 다음 할 일이 없는 건은 '후속 연락 검토'로 표시한다.

종료 코드: 0 성공, 2 입력 오류.
"""
import argparse
import csv
import io
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import InputError, configure_stdout, read_text  # noqa: E402

HEADER = ["company", "title", "url", "source", "applied_on", "status", "next_action_on", "contact", "notes"]
STATUSES = ["관심", "작성중", "지원완료", "서류합격", "면접", "오퍼", "불합격", "보류", "철회"]
CLOSED = {"불합격", "철회"}
MAX_FIELD_LEN = 1000
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def parse_date(value: str, name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise InputError(f"{name} 날짜 형식은 YYYY-MM-DD: {value!r}") from exc


def safe_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection (OWASP 'CSV Injection')."""
    value = value.replace("\x00", "").strip()
    if len(value) > MAX_FIELD_LEN:
        raise InputError(f"값이 너무 김 ({len(value)}자 > {MAX_FIELD_LEN})")
    if value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def validate_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise InputError(f"URL은 http(s)만 허용: {url!r}")
    return url


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    reader = csv.DictReader(io.StringIO(read_text(str(path))))
    missing = [h for h in HEADER if h not in (reader.fieldnames or [])]
    if missing:
        raise InputError(f"트래커 헤더에 열이 없음: {', '.join(missing)} ({path})")
    return list(reader)


def cmd_add(args) -> int:
    path = Path(args.csv)
    if args.status not in STATUSES:
        raise InputError(f"상태는 {', '.join(STATUSES)} 중 하나")
    applied = parse_date(args.applied_on, "--applied-on").isoformat() if args.applied_on else ""
    nxt = parse_date(args.next, "--next").isoformat() if args.next else ""
    row = {
        "company": safe_cell(args.company),
        "title": safe_cell(args.title),
        "url": safe_cell(validate_url(args.url or "")),
        "source": safe_cell(args.source or ""),
        "applied_on": applied,
        "status": args.status,
        "next_action_on": nxt,
        "contact": safe_cell(args.contact or ""),
        "notes": safe_cell(args.notes or ""),
    }
    if not row["company"] or not row["title"]:
        raise InputError("--company와 --title은 비울 수 없음")

    read_rows(path)  # validates the header of an existing file before we append
    new_file = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig on a new file so Excel opens Korean text correctly; plain utf-8 when appending
    # (a BOM in the middle of a file would corrupt the next row).
    with path.open("a", encoding="utf-8-sig" if new_file else "utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    print(f"추가함: {row['company']} / {row['title']} ({row['status']}) → {path}")
    return 0


def cmd_list(args) -> int:
    today = parse_date(args.today, "--today") if args.today else date.today()
    rows = [r for r in read_rows(Path(args.csv)) if r.get("status") not in CLOSED]
    if not rows:
        print("진행 중인 지원 없음")
        return 0

    def sort_key(r):
        return (r.get("next_action_on") or "9999-12-31", r.get("applied_on") or "")

    for r in sorted(rows, key=sort_key):
        flags = []
        nxt = r.get("next_action_on") or ""
        if nxt:
            try:
                d = parse_date(nxt, "next_action_on")
                if d < today:
                    flags.append(f"할 일 {(today - d).days}일 지남")
                elif d == today:
                    flags.append("오늘 할 일")
            except InputError:
                flags.append("next_action_on 형식 오류")
        elif r.get("status") == "지원완료" and r.get("applied_on"):
            try:
                days = (today - parse_date(r["applied_on"], "applied_on")).days
                if days >= args.stale_days:
                    flags.append(f"지원 {days}일 경과: 후속 연락 검토")
            except InputError:
                flags.append("applied_on 형식 오류")
        flag_txt = f"  ← {'; '.join(flags)}" if flags else ""
        print(f"- [{r.get('status')}] {r.get('company')} / {r.get('title')} "
              f"(지원 {r.get('applied_on') or '-'}, 다음 {nxt or '-'}){flag_txt}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description="LinkedIn 지원 현황 기록·조회")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="지원 한 건 추가")
    a.add_argument("csv")
    a.add_argument("--company", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--url")
    a.add_argument("--source", help="예: Easy Apply / 회사 채용페이지 / 리크루터 제안")
    a.add_argument("--status", default="관심")
    a.add_argument("--applied-on")
    a.add_argument("--next", help="다음 할 일 날짜")
    a.add_argument("--contact")
    a.add_argument("--notes")

    lst = sub.add_parser("list", help="진행 중인 지원 보기")
    lst.add_argument("csv")
    lst.add_argument("--stale-days", type=int, default=14)
    lst.add_argument("--today", help="기준일 (테스트용, 기본 오늘)")

    args = ap.parse_args(argv)
    try:
        return cmd_add(args) if args.cmd == "add" else cmd_list(args)
    except InputError as exc:
        print(f"입력 오류: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
