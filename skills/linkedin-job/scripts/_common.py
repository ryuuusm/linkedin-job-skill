"""Shared helpers for the linkedin-job scripts (standard library only).

Kept deliberately small: safe file reading, console encoding, and
markdown-section parsing that every script needs in the same way.
"""
import re
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

# Hard cap on input size. Drafts are a few KB; anything larger is almost
# certainly the wrong file and should not be loaded into memory.
MAX_INPUT_BYTES = 1 * 1024 * 1024

HEADING_RE = re.compile(r"^##\s+(?P<name>[^:：]+?)\s*(?:[:：]\s*(?P<label>.+?))?\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


class InputError(Exception):
    """Raised for user-facing input problems (missing file, bad encoding, too large)."""


class Section(NamedTuple):
    name: str           # heading text before the colon, e.g. "Experience"
    label: str          # text after the colon, e.g. "Senior Analyst @ ACME" ("" if none)
    line: int           # 1-based line number of the heading
    body: str           # content with notes and HTML comments removed


def configure_stdout() -> None:
    """Make Korean output safe on Windows consoles (cp949) and pipes.

    reconfigure() exists on Python 3.7+; we fall back silently if the stream
    does not support it (e.g. when captured by a test harness).
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def read_text(path: str) -> str:
    """Read a UTF-8 text file with a size limit and clear error messages."""
    p = Path(path)
    if not p.is_file():
        raise InputError(f"파일을 찾을 수 없음: {path}")
    size = p.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise InputError(f"파일이 너무 큼 ({size} bytes > {MAX_INPUT_BYTES}): {path}")
    try:
        # utf-8-sig strips a BOM that Windows editors often add.
        return p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError(f"UTF-8로 읽을 수 없음 ({exc.reason}): {path}") from exc


def strip_notes(text: str) -> str:
    """Remove author notes so they are never counted or submitted.

    - HTML comments <!-- ... --> anywhere
    - lines starting with '>' (memo lines, same convention as ai-job-search-kr)
    """
    text = HTML_COMMENT_RE.sub("", text)
    kept = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    return "\n".join(kept)


def parse_sections(text: str) -> List[Section]:
    """Split a draft into '## Name[: label]' sections.

    Headings inside fenced code blocks are ignored. Content before the first
    '##' heading (title, notes) is not a section and is skipped.
    """
    sections: List[Section] = []
    current: Optional[dict] = None
    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            if current is not None:
                sections.append(_close(current))
            current = {"name": m.group("name").strip(), "label": (m.group("label") or "").strip(),
                       "line": no, "lines": []}
        elif current is not None:
            current["lines"].append(line)
    if current is not None:
        sections.append(_close(current))
    return sections


def _close(cur: dict) -> Section:
    body = strip_notes("\n".join(cur["lines"])).strip("\n")
    # Trim trailing whitespace per line; LinkedIn trims it on save as well.
    body = "\n".join(ln.rstrip() for ln in body.splitlines()).strip()
    return Section(cur["name"], cur["label"], cur["line"], body)
