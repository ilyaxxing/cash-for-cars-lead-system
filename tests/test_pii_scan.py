"""The personal data scanner guards every commit; it deserves tests of its own.

Every fake value below is deliberate, hence the pii-allow markers.
"""

import importlib.util
import sys

import pytest

from app.config import BASE_DIR

spec = importlib.util.spec_from_file_location("pii_scan", BASE_DIR / "tools" / "pii_scan.py")
pii_scan = importlib.util.module_from_spec(spec)
# Registered first: dataclasses look their module up while the class is built.
sys.modules["pii_scan"] = pii_scan
spec.loader.exec_module(pii_scan)

FLAGGED = [
    ("call me at (415) 867-5309", "phone number"),  # pii-allow
    ("+1 212 734 2291", "phone number"),  # pii-allow
    ("+7 916 123-45-67", "phone number"),  # pii-allow
    ("write to someone@gmail.com", "email address"),  # pii-allow
    ("ssn 123-45-6789", "social security number"),  # pii-allow
    ("INN 7701234567", "tax identification number"),  # pii-allow
]

ALLOWED = [
    "placeholder (415) 555-0142",
    "fictional +1 212 555 0199",
    "jordan@example.com and team@ops.test",
    "commits as 202311535+ilyaxxing@users.noreply.github.com",
    "released 2026-10-19 at 10:00 on port 5432",
    "price 21,500 and mileage 78,400",
    "build 1792420739013883",
    "placeholder +7 912 345-67-89",
    "demo +49 151 2345 6789 and +55 11 91234-5678",
    "drama +44 7700 900123 and +33 1 99 00 12 34",
]


@pytest.mark.parametrize(("line", "rule"), FLAGGED)
def test_real_looking_personal_data_is_flagged(line, rule):
    assert [found[0] for found in pii_scan.scan_line(line)] == [rule]


@pytest.mark.parametrize("line", ALLOWED)
def test_reserved_and_harmless_values_pass(line):
    assert list(pii_scan.scan_line(line)) == []


def test_marker_allows_a_deliberate_fake():
    assert list(pii_scan.scan_line("someone@gmail.com pii-allow")) == []  # pii-allow


def test_findings_are_redacted():
    [(_, excerpt)] = pii_scan.scan_line("someone@gmail.com")  # pii-allow
    assert "someone" not in excerpt


@pytest.mark.parametrize(
    ("path", "blocked"),
    [
        (".env", True),
        (".env.production", True),
        (".env.example", False),
        ("backups/2026-10-19.sql.gz", True),
        ("data/uploads/1/front.jpg", True),
        ("app/main.py", False),
    ],
)
def test_forbidden_files(path, blocked):
    assert bool(list(pii_scan.check_path(path))) is blocked
