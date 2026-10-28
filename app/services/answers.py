"""Checking form answers against the preset and splitting them for storage.

The form validates as the seller types, but the server is the one that must
not trust anything: answers are re-checked here against the same preset,
unknown keys are dropped, and follow-up answers are kept only when the
question that unlocks them was answered that way.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.db.models import FIXED_ANSWER_COLUMNS
from app.preset.schema import FieldSpec, Preset, Step
from app.services import validation
from app.services.validation import FieldError

# Answer for "older than the year grid goes".
EARLIER = "earlier"

DEFAULT_TEXT_LENGTH = 200
DEFAULT_MULTILINE_LENGTH = 1000


@dataclass(frozen=True)
class AnswerError:
    field: str
    code: str
    params: dict[str, Any] = field(default_factory=dict)


class AnswersInvalid(Exception):
    def __init__(self, errors: list[AnswerError]) -> None:
        super().__init__(", ".join(f"{e.field}:{e.code}" for e in errors))
        self.errors = errors


def steps_until_submit(preset: Preset) -> list[Step]:
    """Steps answered before the lead is saved (the photos come afterwards)."""
    steps = preset.active_steps
    return steps[: steps.index(preset.submit_step) + 1]


def validate_answers(
    preset: Preset,
    raw: Mapping[str, Any],
    *,
    steps: Iterable[Step] | None = None,
    today: datetime | None = None,
) -> dict[str, Any]:
    """Clean answers for the given steps (by default everything up to submit).

    Raises AnswersInvalid listing every problem at once, so the form can show
    them all instead of one per round trip.
    """
    year_now = (today or datetime.now(UTC)).year
    values: dict[str, Any] = {}
    errors: list[AnswerError] = []

    for step in steps if steps is not None else steps_until_submit(preset):
        if not step.enabled:
            continue
        given = {spec.id for spec in step.fields if not _is_empty(raw.get(spec.id))}
        # A skippable step left completely blank was skipped, not half-filled.
        if step.skippable and not given:
            continue
        for spec in step.fields:
            _clean_field(preset, spec, raw, values, errors, year_now)

    # Conditional requirements are checked once every value is known: the
    # field they depend on may come later in the same step.
    already_failed = {error.field for error in errors}
    for spec in preset.all_fields():
        for other_id, expected in (spec.required_when or {}).items():
            missing = spec.id not in values and spec.id not in already_failed
            if missing and values.get(other_id) == expected:
                errors.append(AnswerError(spec.id, "required"))
                already_failed.add(spec.id)

    if errors:
        raise AnswersInvalid(errors)
    return values


def _clean_field(
    preset: Preset,
    spec: FieldSpec,
    raw: Mapping[str, Any],
    values: dict[str, Any],
    errors: list[AnswerError],
    year_now: int,
) -> None:
    if spec.type == "photos":
        return  # uploaded separately, never part of the answers
    value = raw.get(spec.id)
    if _is_empty(value):
        if spec.default is not None:
            values[spec.id] = spec.default
        elif spec.required:
            errors.append(AnswerError(spec.id, "required"))
        return
    try:
        values[spec.id] = _clean_value(preset, spec, value, year_now)
    except FieldError as exc:
        errors.append(AnswerError(spec.id, exc.code, exc.params))
        return
    if spec.follow_up and values[spec.id] == spec.follow_up.when:
        for child in spec.follow_up.fields:
            _clean_field(preset, child, raw, values, errors, year_now)


def _clean_value(preset: Preset, spec: FieldSpec, value: Any, year_now: int) -> Any:
    match spec.type:
        case "text":
            return _clean_text(preset, spec, value)
        case "number":
            return _clean_number(spec, value, year_now)
        case "select" | "yes_no":
            if value not in spec.option_ids:
                raise FieldError("option")
            return value
        case "phone":
            if not isinstance(value, str):
                raise FieldError("format")
            return validation.normalize_phone(value, preset.phone_region)
    raise FieldError("format")  # pragma: no cover - the schema allows no other types


def _clean_text(preset: Preset, spec: FieldSpec, value: Any) -> str:
    if not isinstance(value, str):
        raise FieldError("format")
    if spec.multiline:
        text = "\n".join(line.rstrip() for line in value.strip().splitlines())
        limit = spec.max_length or DEFAULT_MULTILINE_LENGTH
    else:
        text = " ".join(value.split())
        limit = spec.max_length or DEFAULT_TEXT_LENGTH
    if len(text) > limit:
        raise FieldError("too_long", max=limit)
    match spec.format:
        case "vin":
            return validation.normalize_vin(text)
        case "email":
            return validation.normalize_email(text)
        case "postal_code":
            return validation.normalize_postal_code(text, preset.postal_code_rule)
    return text


def _clean_number(spec: FieldSpec, value: Any, year_now: int) -> int | str:
    if spec.earlier is not None and value == EARLIER:
        return EARLIER
    number = validation.parse_int(value)
    low = spec.earlier if spec.earlier is not None else spec.min
    # Model years run ahead of the calendar: next year's cars are on sale now.
    high = year_now + 1 if spec.widget == "year_grid" else spec.max
    if low is not None and number < low:
        raise FieldError("min", value=number, min=low, max=high)
    if high is not None and number > high:
        raise FieldError("max", value=number, min=low, max=high)
    return number


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def split_answers(preset: Preset, values: Mapping[str, Any]) -> tuple[dict[str, Any], dict]:
    """Split clean answers into lead columns and the JSONB remainder.

    Every fixed column the preset knows about is present in the result, set to
    None when unanswered, so an edit that removes an answer clears the column.
    """
    preset_ids = {spec.id for spec in preset.all_fields()}
    columns: dict[str, Any] = {name: None for name in FIXED_ANSWER_COLUMNS if name in preset_ids}
    answers: dict[str, Any] = {}
    for key, value in values.items():
        if value == EARLIER:
            # Kept as "before <year>" so the card can say so; the column stays
            # empty because the real year is unknown.
            answers[f"{key}_before"] = preset.field(key).earlier
            continue
        if key in FIXED_ANSWER_COLUMNS:
            columns[key] = value
        else:
            answers[key] = value
    return columns, answers


def personal_fields(preset: Preset) -> list[str]:
    """Answers that retention erases together with name and phone."""
    return [spec.id for spec in preset.all_fields() if spec.personal]
