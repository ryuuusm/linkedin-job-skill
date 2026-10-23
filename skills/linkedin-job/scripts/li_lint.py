#!/usr/bin/env python3
"""LinkedIn 프로필 초안 글자수·형식 검사 (표준 라이브러리만 사용).

사용법:
    python li_lint.py 프로필초안.md [--limits limits.json] [--json]
    python li_lint.py answers.md --max 500      (Easy Apply 답변: 양식에 보이는 제한을 --max로)

초안 형식 (templates/profile-draft.md 참고):
    ## Headline
    ## About
    ## Experience: <직함> @ <회사>      (경력마다 하나씩)
제목 이름은 limits.json의 aliases로 필드에 연결한다(대소문자 무시, 한글 별칭 가능).
'>'로 시작하는 메모 줄과 <!-- --> 주석은 세지 않는다.

판정:
- ERROR: 제한 초과
- WARN : 제한의 warn_ratio(기본 90%) 이상, 한 줄 필드에 줄바꿈, 빈 섹션
- INFO : LinkedIn이 렌더링하지 않는 마크다운 문법(**굵게**, [링크](url), `코드`, # 제목)

글자수는 NFC 정규화 후 (a) 유니코드 문자 수와 (b) UTF-16 단위 수를 모두 재고,
판정은 더 큰 값(b)으로 한다. 이모지는 UTF-16에서 2단위라 웹 입력창이 더 길게 셀 수 있기 때문이다.

종료 코드: 0 ERROR 없음, 1 ERROR 있음, 2 입력·설정 오류.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import InputError, configure_stdout, parse_sections, read_text  # noqa: E402

DEFAULT_LIMITS = Path(__file__).resolve().parent.parent / "templates" / "limits.json"
MAX_LIMIT_VALUE = 100_000

MARKDOWN_PATTERNS = [
    (re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__"), "굵게(**) 문법은 LinkedIn에서 별표 그대로 보임"),
    (re.compile(r"\[[^\]\n]+\]\([^)\s]+\)"), "[텍스트](url) 링크 문법은 그대로 보임. URL만 쓴다"),
    (re.compile(r"`[^`\n]+`"), "백틱(`)은 그대로 보임"),
    (re.compile(r"^#{1,6}\s", re.M), "# 제목 문법은 그대로 보임"),
]


class Field(NamedTuple):
    key: str
    limit: int
    aliases: List[str]
    single_line: bool


class Result(NamedTuple):
    level: str          # ERROR / WARN / INFO / OK
    line: int
    section: str
    message: str


def count_chars(text: str) -> Dict[str, int]:
    """Return code-point and UTF-16 lengths of NFC-normalized text."""
    norm = unicodedata.normalize("NFC", text)
    return {"chars": len(norm), "utf16": len(norm.encode("utf-16-le")) // 2}


def load_limits(path: Optional[str]):
    """Load and validate limits.json. Raises InputError on any schema problem."""
    src = Path(path) if path else DEFAULT_LIMITS
    try:
        data = json.loads(read_text(str(src)))
    except json.JSONDecodeError as exc:
        raise InputError(f"limits 파일 JSON 오류 ({src}): {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("fields"), dict):
        raise InputError(f"limits 파일에 'fields' 객체가 없음: {src}")

    ratio = data.get("warn_ratio", 0.9)
    if not isinstance(ratio, (int, float)) or not 0 < ratio <= 1:
        raise InputError("warn_ratio는 0보다 크고 1 이하인 숫자여야 함")

    fields: List[Field] = []
    for key, spec in data["fields"].items():
        if not isinstance(spec, dict):
            raise InputError(f"필드 '{key}' 설정이 객체가 아님")
        limit = spec.get("limit")
        # bool is a subclass of int; reject it explicitly.
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= MAX_LIMIT_VALUE:
            raise InputError(f"필드 '{key}'의 limit이 1~{MAX_LIMIT_VALUE} 정수가 아님")
        aliases = spec.get("aliases", [key])
        if not isinstance(aliases, list) or not all(isinstance(a, str) and a.strip() for a in aliases):
            raise InputError(f"필드 '{key}'의 aliases가 문자열 목록이 아님")
        fields.append(Field(key, limit, [a.strip().casefold() for a in aliases] + [key.casefold()],
                            bool(spec.get("single_line", False))))
    return fields, float(ratio)


def match_field(name: str, fields: List[Field]) -> Optional[Field]:
    target = name.strip().casefold()
    for f in fields:
        if target in f.aliases:
            return f
    return None


def lint(text: str, fields: List[Field], warn_ratio: float, default_limit: Optional[int] = None) -> List[Result]:
    """Check every recognised section of a draft against its field limit.

    default_limit applies to sections that match no known field (e.g. Easy Apply
    answers '## Q1: ...' whose limit the user read off the form).
    """
    results: List[Result] = []
    sections = parse_sections(text)
    if not sections:
        return [Result("ERROR", 0, "-", "'## Headline' 같은 섹션 제목이 없음. templates/profile-draft.md 형식을 따른다")]

    for sec in sections:
        title = f"{sec.name}: {sec.label}" if sec.label else sec.name
        field = match_field(sec.name, fields)
        if field is None and default_limit is not None:
            field = Field("custom", default_limit, [], False)
        if field is None:
            results.append(Result("INFO", sec.line, title, "알 수 없는 섹션이라 글자수 검사 생략"))
            continue
        if not sec.body:
            results.append(Result("WARN", sec.line, title, "내용이 비어 있음"))
            continue

        n = count_chars(sec.body)
        used = n["utf16"]  # conservative: never smaller than the code-point count
        detail = f"{n['chars']}자" + (f" (UTF-16 {n['utf16']})" if n["utf16"] != n["chars"] else "")
        if used > field.limit:
            results.append(Result("ERROR", sec.line, title,
                                  f"{detail} / 제한 {field.limit} → {used - field.limit}자 초과"))
        elif used >= field.limit * warn_ratio:
            results.append(Result("WARN", sec.line, title,
                                  f"{detail} / 제한 {field.limit} → 여유 {field.limit - used}자. 저장 시 잘릴 수 있음"))
        else:
            results.append(Result("OK", sec.line, title, f"{detail} / 제한 {field.limit}"))

        if field.single_line and "\n" in sec.body:
            results.append(Result("WARN", sec.line, title, "한 줄 필드인데 줄바꿈이 있음. LinkedIn은 한 줄로 합친다"))
        for pattern, why in MARKDOWN_PATTERNS:
            if pattern.search(sec.body):
                results.append(Result("INFO", sec.line, title, why))
    return results


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description="LinkedIn 프로필 초안 글자수·형식 검사")
    ap.add_argument("draft", help="프로필 초안 Markdown 파일")
    ap.add_argument("--limits", help="필드 제한 JSON (기본: templates/limits.json)")
    ap.add_argument("--max", type=int, help="알려진 필드가 아닌 섹션(예: '## Q1: ...' 답변)에 적용할 글자수 제한")
    ap.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    args = ap.parse_args(argv)

    try:
        if args.max is not None and not 0 < args.max <= MAX_LIMIT_VALUE:
            raise InputError(f"--max는 1~{MAX_LIMIT_VALUE} 사이 정수")
        fields, ratio = load_limits(args.limits)
        results = lint(read_text(args.draft), fields, ratio, args.max)
    except InputError as exc:
        print(f"입력 오류: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([r._asdict() for r in results], ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{r.level:5}] L{r.line:<4} {r.section}: {r.message}")
        errors = sum(r.level == "ERROR" for r in results)
        warns = sum(r.level == "WARN" for r in results)
        print(f"\n요약: ERROR {errors}, WARN {warns}")
    return 1 if any(r.level == "ERROR" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
