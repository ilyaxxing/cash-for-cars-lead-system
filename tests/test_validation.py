import re

import pytest

from app.services.validation import (
    FieldError,
    format_phone,
    normalize_email,
    normalize_phone,
    normalize_postal_code,
    normalize_vin,
    parse_int,
)


@pytest.mark.parametrize(
    "raw",
    ["(415) 555-0142", "415.555.0142", "415 555 0142", "1-415-555-0142", "+1 415 555 0142"],
)
def test_us_phone_formats_normalize_to_e164(raw):
    assert normalize_phone(raw) == "+14155550142"


# Fictional numbers only: UK 020 7946 0xxx is reserved for drama.
@pytest.mark.parametrize(
    "raw",
    ["555-0142", "+44 20 7946 0958", "(015) 555-0142", "(415) 155-0142"],  # pii-allow: fake numbers
)
def test_impossible_us_numbers_are_rejected(raw):
    with pytest.raises(FieldError) as error:
        normalize_phone(raw)
    assert error.value.code == "format"


# Fictional-looking numbers in Russian mobile and Moscow ranges.
@pytest.mark.parametrize(
    "raw",
    ["8 912 345-67-89", "+7 912 345 67 89", "8(912)3456789"],  # pii-allow: fake numbers
)
def test_russian_phone_formats_normalize_to_e164(raw):
    assert normalize_phone(raw, "RU") == "+79123456789"  # pii-allow: fake number


@pytest.mark.parametrize(
    "raw",
    ["12345", "+1 415 555 0142", "8 012 345-67-89"],  # pii-allow: fake numbers
)
def test_impossible_or_foreign_numbers_are_rejected_in_russia(raw):
    with pytest.raises(FieldError):
        normalize_phone(raw, "RU")


def test_vin_is_cleaned_and_upper_cased():
    assert normalize_vin("1hgcm8263-3a004352") == "1HGCM82633A004352"
    assert normalize_vin(" 1HG CM826 33A0 04352 ") == "1HGCM82633A004352"


def test_vin_length_error_reports_the_count():
    with pytest.raises(FieldError) as error:
        normalize_vin("WBA8E5G55KNO1")
    assert (error.value.code, error.value.params) == ("length", {"count": 13})


@pytest.mark.parametrize("raw", ["1HGCM82633A0O4352", "1HGCM82633A0I4352", "1HGCM82633A0Q4352"])
def test_vin_letters_that_never_appear_are_called_out(raw):
    with pytest.raises(FieldError) as error:
        normalize_vin(raw)
    assert error.value.code == "format"


@pytest.mark.parametrize("raw", ["94110", "94110-1234", " 02139 "])
def test_zip_codes(raw):
    assert normalize_postal_code(raw) == raw.strip()


@pytest.mark.parametrize("raw", ["9411", "941100", "ABCDE", "94110-12"])
def test_bad_zip_codes(raw):
    with pytest.raises(FieldError):
        normalize_postal_code(raw)


def test_postal_code_by_pattern():
    six_digits = re.compile(r"\d{6}")
    assert normalize_postal_code(" 101000 ", six_digits) == "101000"
    with pytest.raises(FieldError):
        normalize_postal_code("10100", six_digits)


def test_email_needs_a_complete_domain():
    assert normalize_email(" jordan@example.com ") == "jordan@example.com"
    for raw in ["jordan@", "jordan@example", "jordan example.com"]:
        with pytest.raises(FieldError):
            normalize_email(raw)


@pytest.mark.parametrize(
    ("raw", "expected"), [(78400, 78400), ("78,400", 78400), ("78 400", 78400)]
)
def test_parse_int_accepts_grouped_digits(raw, expected):
    assert parse_int(raw) == expected


@pytest.mark.parametrize("raw", ["7.5", "-3", "abc", True, 7.5, None])
def test_parse_int_rejects_everything_else(raw):
    with pytest.raises(FieldError):
        parse_int(raw)


@pytest.mark.parametrize(
    ("raw", "region", "shown"),
    [
        ("+1 512-555-0100", "US", "(512) 555-0100"),
        ("512.555.0100", "US", "(512) 555-0100"),
        ("+79123456789", "RU", "8 (912) 345-67-89"),  # pii-allow: fake number
        ("+44 7700 900123", "GB", "07700 900123"),  # pii-allow: Ofcom drama range
        ("+442079460958", "US", "+44 20 7946 0958"),  # pii-allow: UK drama range
        ("call the office", "US", "call the office"),
    ],
)
def test_a_phone_reads_in_the_country_format(raw, region, shown):
    # The same as formatPhone in the browser, so a number reads one way everywhere.
    assert format_phone(raw, region) == shown
