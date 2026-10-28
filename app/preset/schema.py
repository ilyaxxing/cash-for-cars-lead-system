"""Shape of a form preset (presets/*.yaml).

A preset is the questionnaire as data: steps, fields, options and a few UI
hints. Both the seller form and the lead card in the dashboard are built from
it. It never contains interface text: every label lives in locales/*.json
under a key derived from the ids used here (see app/preset/texts.py).

Validation is strict on purpose. A typo in a preset should stop the app at
startup, not surface as a broken step in front of a seller.
"""

from __future__ import annotations

import re
from typing import Literal, Self

import phonenumbers
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import FIXED_ANSWER_COLUMNS
from app.services.validation import US_ZIP_RE

ID_PATTERN = r"^[a-z][a-z0-9_]{0,62}$"

FieldType = Literal["text", "number", "select", "yes_no", "photos", "phone"]

# yes_no fields always offer these; "unknown" is added when `unknown: true`.
YES_NO_OPTIONS = ("yes", "no")
YES_NO_UNKNOWN = "unknown"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Option(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    # Optional visual weight, e.g. the condition bars (0 = worst).
    level: int | None = Field(default=None, ge=0, le=4)


class PhotoSlot(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    # Guide illustration file name, served from the form's static assets.
    image: str
    # CSS aspect-ratio of the illustration, e.g. "4 / 3".
    ratio: str = "4 / 3"


class FollowUp(StrictModel):
    """Extra fields shown when the parent field has a given answer."""

    when: str
    fields: list[FieldSpec]


class FieldSpec(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    type: FieldType
    required: bool = False
    # Required only when another field has a given value: {field_id: option_id}.
    required_when: dict[str, str] | None = None
    # Personal data: wiped by retention together with name and phone.
    personal: bool = False

    # select
    options: list[Option] = []
    default: str | None = None
    # yes_no: add a "don't know" answer.
    unknown: bool = False
    # select / yes_no: the answer that raises a warning badge on the lead.
    flag: str | None = None
    follow_up: FollowUp | None = None

    # text
    max_length: int | None = Field(default=None, ge=1, le=5000)
    multiline: bool = False
    format: Literal["vin", "email", "postal_code"] | None = None

    # number
    min: int | None = None
    max: int | None = None
    unit: Literal["distance", "currency"] | None = None
    # Year grid: how many recent years are shown before "show older".
    recent: int | None = Field(default=None, ge=1)
    # Year grid: values below this collapse into a single "earlier" answer.
    earlier: int | None = None

    # UI hint for the form; the server validates by type, not by widget.
    widget: Literal["tiles", "chips", "year_grid"] | None = None
    # Quick picks. A flat list, or per value of another field (suggestions_by).
    suggestions: list[str] | dict[str, list[str]] = []
    suggestions_by: str | None = None
    # tiles: offer "Other" with a free-text answer.
    other: bool = False
    # Show the answer in the running summary at the top of later steps.
    chip: bool = False

    # photos
    slots: list[PhotoSlot] = []
    # Free-form photos on top of the guided slots.
    extra: int = Field(default=0, ge=0)

    @property
    def option_ids(self) -> list[str]:
        if self.type == "yes_no":
            return [*YES_NO_OPTIONS, *([YES_NO_UNKNOWN] if self.unknown else [])]
        return [option.id for option in self.options]

    @property
    def max_photos(self) -> int:
        return len(self.slots) + self.extra

    @model_validator(mode="after")
    def _check_type_specific(self) -> Self:
        if self.type == "select" and not self.options:
            raise ValueError(f"select field {self.id!r} needs options")
        if self.type != "select" and self.options:
            raise ValueError(f"field {self.id!r}: options are only for select fields")
        if self.unknown and self.type != "yes_no":
            raise ValueError(f"field {self.id!r}: unknown is only for yes_no fields")
        for name, value in (("default", self.default), ("flag", self.flag)):
            if value is not None and value not in self.option_ids:
                raise ValueError(f"field {self.id!r}: {name} {value!r} is not an option")
        if self.follow_up and self.follow_up.when not in self.option_ids:
            raise ValueError(
                f"field {self.id!r}: follow_up.when {self.follow_up.when!r} is not an option"
            )
        if self.type == "photos" and not self.max_photos:
            raise ValueError(f"photos field {self.id!r} needs slots or extra")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"field {self.id!r}: min is greater than max")
        if (self.recent or self.earlier) and self.widget != "year_grid":
            raise ValueError(f"field {self.id!r}: recent/earlier need widget year_grid")
        if self.suggestions_by and not isinstance(self.suggestions, dict):
            raise ValueError(f"field {self.id!r}: suggestions_by needs a mapping of suggestions")
        expected = FIXED_ANSWER_COLUMNS.get(self.id)
        if expected is int and self.type != "number":
            raise ValueError(
                f"field {self.id!r} is stored in a numeric column: type must be number"
            )
        if expected is str and self.type not in ("text", "phone"):
            raise ValueError(f"field {self.id!r} is stored in a text column: type must be text")
        if self.id == "phone" and self.type != "phone":
            raise ValueError("field 'phone' must have type phone")
        return self


class Step(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    fields: list[FieldSpec]
    # Off switch for a whole step, e.g. location for a client who does not need it.
    enabled: bool = True
    # The seller may move on without answering.
    skippable: bool = False
    # The lead is saved and the owner notified when this step is submitted.
    submit: bool = False
    # Show the privacy consent checkbox on this step.
    consent: bool = False
    # How the step's note (locale key preset.steps.<id>.note) is drawn.
    note: Literal["box", "icon", "text"] | None = None
    # Show the running summary of earlier answers (fields with chip: true).
    show_chips: bool = False
    # Steps sharing a group are shown as one section on the review screen.
    group: str | None = Field(default=None, pattern=ID_PATTERN)

    @property
    def group_id(self) -> str:
        return self.group or self.id


class Preset(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    version: int = Field(ge=1)
    distance_unit: Literal["mi", "km"]
    # The country sellers' phone numbers belong to (ISO 3166 code: US, RU, DE).
    phone_region: str
    # A US ZIP code, or for another country the postal code as a regular
    # expression (the whole code must match), e.g. '\d{6}' in Russia.
    postal_code_format: Literal["us_zip"] | None = None
    postal_code_pattern: str | None = None
    steps: list[Step]

    @field_validator("phone_region")
    @classmethod
    def _check_phone_region(cls, value: str) -> str:
        if value not in phonenumbers.SUPPORTED_REGIONS:
            raise ValueError(f"phone_region {value!r} is not a country code such as US or RU")
        return value

    @field_validator("postal_code_pattern")
    @classmethod
    def _check_postal_code_pattern(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"postal_code_pattern is not a valid pattern: {exc}") from None
        return value

    @property
    def postal_code_rule(self) -> re.Pattern[str]:
        """What a postal code must match: the preset's pattern, or a US ZIP code."""
        return re.compile(self.postal_code_pattern) if self.postal_code_pattern else US_ZIP_RE

    @property
    def active_steps(self) -> list[Step]:
        return [step for step in self.steps if step.enabled]

    def all_fields(self) -> list[FieldSpec]:
        """Every field in preset order, follow-ups right after their parent."""
        return [spec for step in self.steps for spec in _with_follow_ups(step.fields)]

    def field(self, field_id: str) -> FieldSpec:
        for spec in self.all_fields():
            if spec.id == field_id:
                return spec
        raise KeyError(field_id)

    @property
    def submit_step(self) -> Step:
        return next(step for step in self.steps if step.submit)

    @model_validator(mode="after")
    def _check_structure(self) -> Self:
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("step ids must be unique")

        fields = self.all_fields()
        field_ids = [spec.id for spec in fields]
        duplicates = sorted({fid for fid in field_ids if field_ids.count(fid) > 1})
        if duplicates:
            raise ValueError(f"field ids must be unique across the preset: {duplicates}")

        if self.postal_code_format and self.postal_code_pattern:
            raise ValueError("use postal_code_format or postal_code_pattern, not both")

        submit_steps = [step for step in self.steps if step.submit]
        if len(submit_steps) != 1:
            raise ValueError("exactly one step must have submit: true")
        submit_step = submit_steps[0]
        if not submit_step.enabled:
            raise ValueError("the submit step cannot be disabled")
        if not submit_step.consent:
            raise ValueError("the submit step must ask for consent")

        submit_index = self.steps.index(submit_step)
        before_submit = {
            spec.id
            for step in self.steps[: submit_index + 1]
            for spec in _with_follow_ups(step.fields)
        }
        if "phone" not in before_submit:
            raise ValueError("a phone field is required at or before the submit step")
        # Photos are uploaded to an existing lead, so they come after it is saved.
        for step in self.steps[: submit_index + 1]:
            if any(spec.type == "photos" for spec in step.fields):
                raise ValueError("photos must come after the submit step")
        for step in self.steps[submit_index + 1 :]:
            if any(spec.type != "photos" for spec in _with_follow_ups(step.fields)):
                raise ValueError("only photos can come after the submit step")
        if sum(spec.type == "photos" for spec in fields) > 1:
            raise ValueError("a preset can have at most one photos field")

        known = set(field_ids)
        for spec in fields:
            if spec.suggestions_by and spec.suggestions_by not in known:
                raise ValueError(f"field {spec.id!r}: suggestions_by refers to an unknown field")
            for other_id, value in (spec.required_when or {}).items():
                if other_id not in known:
                    raise ValueError(f"field {spec.id!r}: required_when refers to {other_id!r}")
                if value not in self.field(other_id).option_ids:
                    raise ValueError(f"field {spec.id!r}: required_when value {value!r} unknown")
            if spec.format == "postal_code" and not (
                self.postal_code_format or self.postal_code_pattern
            ):
                raise ValueError(
                    "postal_code fields need postal_code_format or postal_code_pattern"
                )
        return self


def _with_follow_ups(fields: list[FieldSpec]) -> list[FieldSpec]:
    result = []
    for spec in fields:
        result.append(spec)
        if spec.follow_up:
            result.extend(spec.follow_up.fields)
    return result


FollowUp.model_rebuild()
