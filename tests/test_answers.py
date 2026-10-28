from datetime import UTC, datetime

import pytest

from app.services.answers import (
    EARLIER,
    AnswersInvalid,
    personal_fields,
    split_answers,
    validate_answers,
)
from tests.conftest import step_of

TODAY = datetime(2026, 10, 19, tzinfo=UTC)

COMPLETE = {
    "make": "Toyota",
    "model": " Camry ",
    "year": 2019,
    "mileage": "78,400",
    "condition": "good",
    "accident": "no",
    "finance": "no",
    "asking_price": "21,500",
    "location": "San Francisco",
    "postal_code": "94110",
    "vin": "1hgcm82633a004352",
    "name": "Jordan  Lee",
    "phone": "(415) 555-0142",
    "contact_method": "whatsapp",
}


def errors_of(preset, raw):
    with pytest.raises(AnswersInvalid) as caught:
        validate_answers(preset, raw, today=TODAY)
    return {(error.field, error.code) for error in caught.value.errors}


def test_complete_answers_are_cleaned(preset):
    values = validate_answers(preset, COMPLETE, today=TODAY)
    assert values["model"] == "Camry"
    assert values["mileage"] == 78400
    assert values["asking_price"] == 21500
    assert values["vin"] == "1HGCM82633A004352"
    assert values["name"] == "Jordan Lee"
    assert values["phone"] == "+14155550142"


def test_answers_split_between_columns_and_jsonb(preset):
    columns, answers = split_answers(preset, validate_answers(preset, COMPLETE, today=TODAY))
    assert columns == {
        "make": "Toyota",
        "model": "Camry",
        "year": 2019,
        "mileage": 78400,
        "asking_price": 21500,
        "location": "San Francisco",
        "phone": "+14155550142",
        "name": "Jordan Lee",
    }
    assert answers == {
        "condition": "good",
        "accident": "no",
        "finance": "no",
        "postal_code": "94110",
        "vin": "1HGCM82633A004352",
        "contact_method": "whatsapp",
    }


def test_unknown_keys_never_reach_storage(preset):
    values = validate_answers(
        preset, {**COMPLETE, "is_admin": True, "status": "bought"}, today=TODAY
    )
    assert "is_admin" not in values and "status" not in values


def test_all_problems_are_reported_together(preset):
    raw = {**COMPLETE, "make": "", "mileage": "lots", "condition": "mint", "phone": "12"}
    assert errors_of(preset, raw) == {
        ("make", "required"),
        ("mileage", "format"),
        ("condition", "option"),
        ("phone", "format"),
    }


def test_follow_up_is_kept_only_after_the_unlocking_answer(preset):
    details = {"accident_details": "Rear bumper scuff", "finance_details": "Loan"}
    values = validate_answers(preset, {**COMPLETE, **details, "accident": "yes"}, today=TODAY)
    assert values["accident_details"] == "Rear bumper scuff"
    assert "finance_details" not in values  # finance was "no"


def test_dont_know_is_a_valid_answer(preset):
    values = validate_answers(preset, {**COMPLETE, "accident": "unknown"}, today=TODAY)
    assert values["accident"] == "unknown"


def test_skipped_steps_leave_nothing_behind(preset):
    raw = {**COMPLETE, "asking_price": "", "location": "", "postal_code": "", "vin": ""}
    values = validate_answers(preset, raw, today=TODAY)
    assert not {"asking_price", "location", "postal_code", "vin"} & values.keys()


def test_half_filled_skippable_step_must_be_completed(preset):
    assert errors_of(preset, {**COMPLETE, "postal_code": ""}) == {("postal_code", "required")}


def test_email_is_required_only_when_preferred(preset):
    assert errors_of(preset, {**COMPLETE, "contact_method": "email"}) == {("email", "required")}
    values = validate_answers(preset, {**COMPLETE, "contact_method": "call"}, today=TODAY)
    assert "email" not in values


def test_contact_method_defaults_to_a_call(preset):
    values = validate_answers(preset, {**COMPLETE, "contact_method": None}, today=TODAY)
    assert values["contact_method"] == "call"


def test_number_limits(preset):
    assert errors_of(preset, {**COMPLETE, "mileage": "990,000"}) == {("mileage", "max")}
    assert errors_of(preset, {**COMPLETE, "asking_price": "50"}) == {("asking_price", "min")}


def test_next_model_year_is_accepted_but_not_later(preset):
    assert validate_answers(preset, {**COMPLETE, "year": 2027}, today=TODAY)["year"] == 2027
    assert errors_of(preset, {**COMPLETE, "year": 2028}) == {("year", "max")}
    assert errors_of(preset, {**COMPLETE, "year": 1985}) == {("year", "min")}


def test_earlier_year_keeps_the_column_empty(preset):
    values = validate_answers(preset, {**COMPLETE, "year": EARLIER}, today=TODAY)
    columns, answers = split_answers(preset, values)
    assert columns["year"] is None
    assert answers["year_before"] == 1990


def test_disabled_step_is_ignored(build_preset):
    preset = build_preset(lambda d: step_of(d, "location").update(enabled=False))
    values = validate_answers(preset, {**COMPLETE, "postal_code": "bad"}, today=TODAY)
    assert "location" not in values and "postal_code" not in values


def test_personal_fields_include_email(preset):
    assert personal_fields(preset) == ["name", "phone", "email"]


def test_telegram_is_a_contact_method_only_where_the_preset_offers_it(preset, build_preset):
    from tests.test_preset import with_telegram

    raw = {**COMPLETE, "contact_method": "telegram"}
    assert errors_of(preset, raw) == {("contact_method", "option")}
    cleaned = validate_answers(build_preset(with_telegram), raw, today=TODAY)
    assert cleaned["contact_method"] == "telegram"
