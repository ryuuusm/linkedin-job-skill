#!/usr/bin/env python3
"""LinkedIn 프로필·지원서 답변 제출 전 자동 검사 (표준 라이브러리만 사용).

사용법:
    python precheck.py 프로필초안.md 답변.md [--profile profile.md] [--target 회사명]
                       [--companies "A사,B Corp"] [--tracker applications/tracker.csv]
                       [--keywords "SAP,ITGC,Python"] [--public]

검사 (규칙 근거: references/02-writing-style.md, references/06-trust-and-policy.md)
- ERROR: 채우지 않은 자리표시([미입력], TODO, {{...}}), 주민등록번호·카드번호 형태의 숫자,
         --target 외 다른 회사명(--companies, --tracker에서 수집)
- WARN : 상투어(한/영), --profile에 없는 숫자(지어낸 수치 의심),
         --public일 때 공개 프로필에 이메일·휴대폰 번호
- INFO : --keywords 커버리지(반영됨/누락)
'>' 메모 줄과 <!-- --> 주석은 검사에서 뺀다(제출되지 않는 내용).

종료 코드: 0 ERROR 없음, 1 ERROR 있음, 2 입력 오류.
"""
import argparse
import csv
import io
import re
import sys
import unicodedata
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import InputError, configure_stdout, read_text, strip_notes  # noqa: E402

PLACEHOLDER_RE = re.compile(
    r"\[(미입력|미정|TODO|TBD|확인 ?필요|이름|회사|직함|Name|Company|Title)\]|\bTODO\b|\bTBD\b|\{\{[^}]*\}\}",
    re.I)
RRN_RE = re.compile(r"(?<!\d)\d{6}-?[1-4]\d{6}(?!\d)")
CARD_CANDIDATE_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
KR_MOBILE_RE = re.compile(r"(?<!\d)(?:\+82[ -]?1|01)[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)")
NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*")

# Clichés: (pattern, suggestion). English patterns are matched case-insensitively
# on word boundaries; Korean ones as substrings.
CLICHES_EN = {
    "passionate": "show the evidence of passion instead",
    "results-driven": "state the result",
    "detail-oriented": "give one example of a caught mistake",
    "team player": "describe what you did in the team",
    "hard-working": "show output, not effort",
    "go-getter": "remove",
    "synergy": "name the concrete outcome",
    "thought leader": "let others say it; show the work",
    "guru": "remove",
    "ninja": "remove",
    "rockstar": "remove",
    "seasoned professional": "state years and domain",
    "dynamic": "remove or make concrete",
    "think outside the box": "describe the unusual approach",
}
CLICHES_KO = {
    "열정": "열정을 보여준 사례로 바꾼다",
    "성실함": "사례로 바꾼다",
    "책임감이 강한": "책임을 진 사례로 바꾼다",
    "소통을 잘하는": "조율한 사례로 바꾼다",
    "최선을 다하겠습니다": "할 일을 구체적으로 쓴다",
    "누구보다": "비교 근거가 있는 수치로 바꾼다",
    "최고의 인재": "삭제",
    "글로벌 인재": "근거 경험으로 바꾼다",
    "시너지": "구체적 결과로 바꾼다",
}


class Finding(NamedTuple):
    level: str
    file: str
    line: int
    rule: str
    text: str


def luhn_ok(digits: str) -> bool:
    """Luhn checksum; filters out ordinary long numbers that are not card numbers."""
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def normalize_number(token: str) -> str:
    """'1,200' -> '1200', '3.5' stays '3.5'. Used to compare draft vs profile numbers."""
    return token.replace(",", "")


def numbers_in(text: str) -> Set[str]:
    return {normalize_number(m.group(0)) for m in NUMBER_RE.finditer(text)}


def load_companies(csv_path: Optional[str], extra: Optional[str]) -> Set[str]:
    """Collect company names from tracker CSV ('company' or '회사' column) and --companies."""
    names: Set[str] = set()
    if extra:
        names.update(n.strip() for n in extra.split(",") if n.strip())
    if csv_path:
        reader = csv.DictReader(io.StringIO(read_text(csv_path)))
        col = next((c for c in (reader.fieldnames or []) if c.strip().lower() in ("company", "회사")), None)
        if col is None:
            raise InputError(f"트래커에 company(회사) 열이 없음: {csv_path}")
        for row in reader:
            name = (row.get(col) or "").strip()
            if name:
                names.add(name)
    return names


def company_pattern(name: str) -> re.Pattern:
    """Latin names need word boundaries ('Meta' must not match 'metadata')."""
    esc = re.escape(name)
    if re.search(r"[A-Za-z]", name):
        return re.compile(rf"(?<![A-Za-z0-9]){esc}(?![A-Za-z0-9])", re.I)
    return re.compile(esc)


def check_text(fname: str, raw: str, *, others: Iterable[str], profile_numbers: Optional[Set[str]],
               public: bool) -> List[Finding]:
    """Run all line-level checks on one file."""
    out: List[Finding] = []
    text = unicodedata.normalize("NFC", strip_notes(raw))
    other_patterns = [(n, company_pattern(n)) for n in others]
    for no, line in enumerate(text.splitlines(), 1):
        for m in PLACEHOLDER_RE.finditer(line):
            out.append(Finding("ERROR", fname, no, "자리표시", m.group(0)))
        for m in RRN_RE.finditer(line):
            out.append(Finding("ERROR", fname, no, "주민등록번호 형태", "삭제한다. LinkedIn에 절대 쓰지 않음"))
        for m in CARD_CANDIDATE_RE.finditer(line):
            digits = re.sub(r"\D", "", m.group(0))
            if 13 <= len(digits) <= 19 and luhn_ok(digits):
                out.append(Finding("ERROR", fname, no, "카드번호 형태", "삭제한다"))
        for name, pat in other_patterns:
            if pat.search(line):
                out.append(Finding("ERROR", fname, no, "다른 회사명", name))
        lower = line.lower()
        for word, tip in CLICHES_EN.items():
            if re.search(rf"\b{re.escape(word)}\b", lower):
                out.append(Finding("WARN", fname, no, "상투어", f"'{word}' → {tip}"))
        for word, tip in CLICHES_KO.items():
            if word in line:
                out.append(Finding("WARN", fname, no, "상투어", f"'{word}' → {tip}"))
        if public:
            if EMAIL_RE.search(line):
                out.append(Finding("WARN", fname, no, "공개 연락처", "이메일이 공개 프로필에 노출됨. Contact info 칸을 쓴다"))
            if KR_MOBILE_RE.search(line):
                out.append(Finding("WARN", fname, no, "공개 연락처", "휴대폰 번호가 공개 프로필에 노출됨"))
        if profile_numbers is not None:
            for num in sorted(numbers_in(line) - profile_numbers):
                out.append(Finding("WARN", fname, no, "프로필에 없는 숫자",
                                   f"'{num}' 근거를 profile.md에서 찾지 못함. 지어낸 수치인지 확인"))
    return out


def keyword_coverage(texts: List[str], keywords: List[str]) -> List[Finding]:
    joined = unicodedata.normalize("NFC", "\n".join(strip_notes(t) for t in texts)).casefold()
    hit = [k for k in keywords if k.casefold() in joined]
    miss = [k for k in keywords if k.casefold() not in joined]
    res = [Finding("INFO", "-", 0, "키워드 반영", ", ".join(hit) or "없음")]
    if miss:
        res.append(Finding("INFO", "-", 0, "키워드 누락",
                           ", ".join(miss) + " (프로필 근거가 있을 때만 추가한다)"))
    return res


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description="LinkedIn 프로필·지원서 답변 제출 전 검사")
    ap.add_argument("files", nargs="+", help="검사할 Markdown/텍스트 파일")
    ap.add_argument("--profile", help="사실 근거 profile.md (숫자 대조)")
    ap.add_argument("--target", help="지원 회사명 (다른 회사명 검사에서 제외)")
    ap.add_argument("--companies", help="쉼표로 구분한 다른 회사명")
    ap.add_argument("--tracker", help="지원 현황 CSV (company 열에서 회사명 수집)")
    ap.add_argument("--keywords", help="쉼표로 구분한 공고 핵심 키워드")
    ap.add_argument("--public", action="store_true", help="공개 프로필 문서로 보고 연락처 노출 검사")
    args = ap.parse_args(argv)

    try:
        companies = load_companies(args.tracker, args.companies)
        target = (args.target or "").strip().casefold()
        others = sorted(c for c in companies if c.casefold() != target
                        and (not target or target not in c.casefold()))
        profile_numbers = numbers_in(read_text(args.profile)) if args.profile else None
        texts = {f: read_text(f) for f in args.files}
    except InputError as exc:
        print(f"입력 오류: {exc}", file=sys.stderr)
        return 2

    findings: List[Finding] = []
    for fname, raw in texts.items():
        findings += check_text(fname, raw, others=others, profile_numbers=profile_numbers, public=args.public)
    if args.keywords:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        findings += keyword_coverage(list(texts.values()), kws)

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for f in sorted(findings, key=lambda x: (order[x.level], x.file, x.line)):
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"[{f.level:5}] {loc} {f.rule}: {f.text}")
    errors = sum(f.level == "ERROR" for f in findings)
    warns = sum(f.level == "WARN" for f in findings)
    print(f"\n요약: ERROR {errors}, WARN {warns}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
