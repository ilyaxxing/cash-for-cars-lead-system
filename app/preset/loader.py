"""Loading a preset and checking that the locale has text for all of it."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.i18n import Messages
from app.preset.schema import Preset


class PresetError(Exception):
    """The preset cannot be used; raised at startup."""


def load_preset(presets_dir: Path, name: str, file: Path | None = None) -> Preset:
    """The shipped preset `name`, or a client's own preset file when given."""
    path = file or presets_dir / f"{name}.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        setting = "PRESET_FILE" if file else f"PRESET={name!r}"
        raise PresetError(f"preset file {path} not found ({setting})") from exc
    except yaml.YAMLError as exc:
        raise PresetError(f"preset file {path} is not valid YAML: {exc}") from exc
    try:
        preset = Preset.model_validate(raw)
    except ValidationError as exc:
        raise PresetError(f"preset file {path} is invalid:\n{exc}") from exc
    if file is None and preset.id != name:
        raise PresetError(f"preset file {path} declares id {preset.id!r}, expected {name!r}")
    return preset


def required_text_keys(preset: Preset) -> list[str]:
    """Locale keys the form and the lead card cannot do without.

    Hints, placeholders and per-field error messages are optional and fall
    back to generic text; titles, labels and option names are not.
    """
    keys = []
    for step in preset.steps:
        keys.append(f"preset.steps.{step.id}.title")
    for spec in preset.all_fields():
        keys.append(f"preset.fields.{spec.id}.label")
        if spec.type == "select":
            keys += [f"preset.options.{spec.id}.{option}.label" for option in spec.option_ids]
        if spec.type == "yes_no":
            keys += [f"preset.yes_no.{option}" for option in spec.option_ids]
        if spec.flag:
            keys.append(f"preset.flags.{spec.id}")
        for slot in spec.slots:
            keys += [f"preset.photos.{slot.id}.label", f"preset.photos.{slot.id}.tip"]
    return list(dict.fromkeys(keys))


def check_texts(preset: Preset, messages: Messages) -> None:
    missing = [key for key in required_text_keys(preset) if not messages.has(key)]
    if missing:
        listed = "\n  ".join(missing)
        raise PresetError(
            f"locale {messages.locale!r} has no text for preset {preset.id!r}:\n  {listed}"
        )
