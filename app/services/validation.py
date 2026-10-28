"""Normalizing single answers: phone numbers, VINs, postal codes, emails, numbers.

Each function either returns a clean value or raises FieldError with a code.
The code (not a message) goes back to the form, which looks up the text in the
locale: the server never decides how an error is worded.
"""

from __future__ import annotations

import re
from typing import Any

import phonenumbers


class FieldError(Exception):
    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


# VINs never contain I, O or Q: they were left out so they cannot be confused
# with 1 and 0. Seeing one is almost always a typo, and worth saying so.
VIN_LENGTH = 17
VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

US_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")

# Deliberately loose: the goal is to catch an unfinished address, not to
# re-implement RFC 5322. The buyer will see it and can always call instead.
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def parse_int(raw: Any) -> int:
    """An integer from a number or from text like "78,400" or "78 400"."""
    if isinstance(raw, bool):
        raise FieldError("format")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        digits = re.sub(r"[\s,_]", "", raw)
        if digits.isdigit():
            return int(digits)
    raise FieldError("format")


def normalize_vin(raw: str) -> str:
    """Upper-case VIN without spaces and dashes.

    Checked in an order that gives the most useful message: length first,
    then the characters a VIN never uses.
    """
    value = re.sub(r"[\s-]", "", raw).upper()
    if len(value) != VIN_LENGTH:
        raise FieldError("length", count=len(value))
    if not VIN_RE.match(value):
        raise FieldError("format")
    return value


def normalize_phone(raw: str, region: str = "US") -> str:
    """E.164 form (+14155550142) of a number typed the way people do in `region`.

    (415) 555-0142, 415.555.0142, 1-415-555-0142 or +1 415 555 0142 in the
    US; ten digits after 8 or +7 in Russia. The rules are
    libphonenumber's, so a number that cannot exist (a US area code starting
    with 0 or 1) is refused, and so is a number from a country with another
    calling code: the business calls sellers near it.
    """
    try:
        number = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException:
        raise FieldError("format") from None
    home = phonenumbers.country_code_for_region(region)
    if number.country_code != home or not phonenumbers.is_valid_number(number):
        raise FieldError("format")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def normalize_postal_code(raw: str, rule: re.Pattern[str] = US_ZIP_RE) -> str:
    """A postal code that matches the preset's rule (a US ZIP code by default)."""
    value = raw.strip()
    if not rule.fullmatch(value):
        raise FieldError("format")
    return value


def normalize_email(raw: str) -> str:
    value = raw.strip()
    if not EMAIL_RE.match(value):
        raise FieldError("format")
    return value
