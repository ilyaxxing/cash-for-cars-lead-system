"""Scan changes for personal data before they reach the repository.

gitleaks catches credentials. This script catches the other thing that must
never be committed: real people's data. Sellers' names, phone numbers and
email addresses end up in fixtures, logs and copy-pasted examples far more
often than anyone intends, and once pushed they stay in git history.

Usage:
    python3 tools/pii_scan.py --staged    # added lines in the staged diff
    python3 tools/pii_scan.py --tracked   # every tracked file

Deliberate fake data is allowed in two ways:
    - use reserved values: example.com / .test emails, 555-01xx phone numbers,
      the UK's and France's ranges for fiction, or a number with an obvious
      run of digits such as +49 151 2345 6789 (the demo countries use these)
    - or put the marker "pii-allow" on the line, with a reason nearby

Runs on the system Python, so it sticks to the standard library and to
syntax that Python 3.9 understands.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

ALLOW_MARKER = "pii-allow"

# Files that must never be committed, even with `git add --force`.
FORBIDDEN_PATHS = [
    (re.compile(r"(^|/)\.env$"), "environment file"),
    (re.compile(r"(^|/)\.env\.(?!example$)[^/]+$"), "environment file"),
    (re.compile(r"\.(sql|sql\.gz|dump|backup)$"), "database dump"),
    (re.compile(r"^(data|uploads|backups)/"), "uploaded or exported data"),
]

# Lock files are machine-generated and full of hashes that look like noise.
SKIPPED_FILES = re.compile(r"(^|/)(package-lock\.json|.*\.lock)$")

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
ALLOWED_EMAIL_DOMAINS = re.compile(
    r"(^|\.)(example\.(com|org|net)|example|test|invalid|localhost"
    r"|users\.noreply\.github\.com|github\.com)$",
    re.IGNORECASE,
)

# North American numbers with separators: (415) 555-0142, 415-555-0142, +1 415 555 0142.
# A number ends where a word or more digits do not go on; a full stop after
# it ends the sentence ("for example +7 912 345-67-89.").
NANP_PHONE = re.compile(
    r"(?<![\w.])(?:\+?1[\s.-]?)?\(?(\d{3})\)?[\s.-](\d{3})[\s.-](\d{4})(?!\w|\.\d)"
)
# Any other international number written with a leading plus.
INTL_PHONE = re.compile(r"(?<![\w.])\+\d[\d\s().-]{9,}\d(?!\w|\.\d)")
# 555-0100 through 555-0199 are reserved for fiction in North America.
FICTIONAL_NANP = re.compile(r"555[\s.)-]*01\d\d\b")
# Elsewhere: Ofcom's drama range (07700 900000-900999), ARCEP's (01 99 00 ..),
# and numbers written as obvious examples, with eight ascending digits in a row.
FICTIONAL_INTL = re.compile(r"\+44[\s.-]?7700[\s.-]?900[\s.-]?\d{3}|\+33[\s.-]?1[\s.-]?99[\s.-]?00")
EXAMPLE_RUNS = ("12345678", "23456789")


def fictional_intl(number: str) -> bool:
    digits = re.sub(r"\D", "", number)
    return bool(FICTIONAL_INTL.search(number)) or any(run in digits for run in EXAMPLE_RUNS)


SSN = re.compile(r"(?<![\w-])\d{3}-\d{2}-\d{4}(?![\w-])")
TAX_ID = re.compile(r"\b(?:INN|ИНН)\D{0,3}\d{10,12}\b", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    excerpt: str

    def __str__(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"{location}: {self.rule}: {self.excerpt}"


def redact(value: str) -> str:
    """Keep enough to find the spot, not enough to leak the value again."""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def scan_line(text: str) -> Iterator[tuple[str, str]]:
    if ALLOW_MARKER in text:
        return
    for match in EMAIL.finditer(text):
        if not ALLOWED_EMAIL_DOMAINS.search(match.group(1)):
            yield "email address", redact(match.group(0))
    for match in NANP_PHONE.finditer(text):
        if not FICTIONAL_NANP.search(match.group(0)):
            yield "phone number", redact(match.group(0))
    for match in INTL_PHONE.finditer(text):
        if NANP_PHONE.search(match.group(0)) or FICTIONAL_NANP.search(match.group(0)):
            continue  # already judged by the NANP rule above
        if fictional_intl(match.group(0)):
            continue
        yield "phone number", redact(match.group(0))
    for match in SSN.finditer(text):
        yield "social security number", redact(match.group(0))
    for match in TAX_ID.finditer(text):
        yield "tax identification number", redact(match.group(0))


def check_path(path: str) -> Iterator[Finding]:
    for pattern, what in FORBIDDEN_PATHS:
        if pattern.search(path):
            yield Finding(path, 0, f"{what} must not be committed", path)


def scan_lines(path: str, lines: Iterable[tuple[int, str]]) -> Iterator[Finding]:
    if SKIPPED_FILES.search(path):
        return
    for number, text in lines:
        for rule, excerpt in scan_line(text):
            yield Finding(path, number, rule, excerpt)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def staged_findings() -> Iterator[Finding]:
    for path in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines():
        yield from check_path(path)

    diff = git("diff", "--cached", "--unified=0", "--no-color", "--diff-filter=ACMR")
    path = ""
    line_no = 0
    added: list[tuple[int, str]] = []
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            if path:
                yield from scan_lines(path, added)
            path = raw[6:] if raw.startswith("+++ b/") else ""
            added = []
        elif raw.startswith("@@"):
            hunk = re.search(r"\+(\d+)", raw)
            line_no = int(hunk.group(1)) if hunk else 0
        elif raw.startswith("+") and path:
            added.append((line_no, raw[1:]))
            line_no += 1
    if path:
        yield from scan_lines(path, added)


def tracked_findings() -> Iterator[Finding]:
    for path in git("ls-files").splitlines():
        yield from check_path(path)
        try:
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue  # binary files and submodules are out of scope
        yield from scan_lines(path, enumerate(content.splitlines(), start=1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="scan the staged diff")
    group.add_argument("--tracked", action="store_true", help="scan all tracked files")
    args = parser.parse_args(argv)

    findings = list(staged_findings() if args.staged else tracked_findings())
    if not findings:
        return 0
    print("Possible personal data found:", file=sys.stderr)
    for finding in findings:
        print(f"  {finding}", file=sys.stderr)
    print(
        f"\nReplace real data with reserved values (example.com, 555-01xx) or mark a "
        f"deliberate fake with '{ALLOW_MARKER}' on the same line.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
