from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.config import BASE_DIR
from app.i18n import Messages, load_messages
from app.preset.loader import PresetError, check_texts, load_preset, required_text_keys
from tests.conftest import step_of


def test_shipped_preset_loads_and_has_texts():
    preset = load_preset(BASE_DIR / "presets", "us-car-buyout")
    check_texts(preset, load_messages(BASE_DIR / "locales", "en"))
    assert preset.submit_step.id == "contact"
    assert preset.field("photos").max_photos == 10  # six guided angles plus four extra


def test_flow_follows_the_agreed_order(preset):
    assert [step.id for step in preset.steps] == [
        "vehicle",
        "year_mileage",
        "condition",
        "accident",
        "finance",
        "price",
        "location",
        "vin",
        "contact",
        "photos",
    ]


def test_accident_and_lien_offer_dont_know(preset):
    assert preset.field("accident").option_ids == ["yes", "no", "unknown"]
    assert preset.field("finance").option_ids == ["yes", "no", "unknown"]


def test_missing_text_is_reported_by_key(preset):
    with pytest.raises(PresetError, match=r"preset\.steps\.vehicle\.title"):
        check_texts(preset, Messages("en", {}))


def test_required_keys_cover_options_flags_and_photo_slots(preset):
    keys = required_text_keys(preset)
    assert "preset.options.condition.not_running.label" in keys
    assert "preset.yes_no.unknown" in keys
    assert "preset.flags.accident" in keys
    assert "preset.photos.cluster.tip" in keys


def test_loader_rejects_file_with_another_id(tmp_path: Path, preset_data):
    (tmp_path / "other.yaml").write_text(yaml.safe_dump(preset_data), encoding="utf-8")
    with pytest.raises(PresetError, match="declares id"):
        load_preset(tmp_path, "other")


def test_loader_explains_a_missing_file(tmp_path: Path):
    with pytest.raises(PresetError, match="not found"):
        load_preset(tmp_path, "nowhere")


def with_telegram(data):
    """What an installer adds for a client whose sellers use Telegram."""
    for step in data["steps"]:
        for field in step["fields"]:
            if field["id"] == "contact_method":
                field["options"].insert(3, {"id": "telegram"})


def test_telegram_can_be_offered_without_new_texts(build_preset):
    preset = build_preset(with_telegram)
    methods = preset.field("contact_method").option_ids
    assert methods == ["call", "sms", "whatsapp", "telegram", "email"]
    check_texts(preset, load_messages(BASE_DIR / "locales", "en"))


def test_new_question_is_just_preset_data(build_preset):
    def add_question(data):
        step_of(data, "condition")["fields"].append(
            {"id": "keys", "type": "select", "options": [{"id": "one"}, {"id": "two"}]}
        )

    assert build_preset(add_question).field("keys").option_ids == ["one", "two"]


def _field(data, step_id, field_id):
    return next(f for f in step_of(data, step_id)["fields"] if f["id"] == field_id)


BROKEN_PRESETS = {
    "unknown field type": lambda d: _field(d, "vin", "vin").update(type="date"),
    "duplicate field id": lambda d: _field(d, "vin", "vin").update(id="make"),
    "select without options": lambda d: _field(d, "condition", "condition").update(options=[]),
    "year stored as text": lambda d: _field(d, "year_mileage", "year").update(
        type="text", widget=None, recent=None, earlier=None
    ),
    "flag is not an option": lambda d: _field(d, "accident", "accident").update(flag="maybe"),
    "follow-up on unknown answer": lambda d: _field(d, "accident", "accident")["follow_up"].update(
        when="maybe"
    ),
    "required_when unknown field": lambda d: _field(d, "contact", "email").update(
        required_when={"pager": "email"}
    ),
    "no submit step": lambda d: step_of(d, "contact").update(submit=False),
    "two submit steps": lambda d: step_of(d, "vin").update(submit=True, consent=True),
    "submit step without consent": lambda d: step_of(d, "contact").update(consent=False),
    "photos before the lead exists": lambda d: d["steps"].insert(0, d["steps"].pop()),
    "unknown attribute": lambda d: _field(d, "vin", "vin").update(color="red"),
    "postal code without format": lambda d: d.pop("postal_code_format"),
    "postal code with two rules": lambda d: d.update(postal_code_pattern=r"\d{5}"),
    "postal code pattern that is not one": lambda d: d.update(
        postal_code_format=None, postal_code_pattern="([0-9]"
    ),
    "phone region that is not a country": lambda d: d.update(phone_region="USA"),
}


@pytest.mark.parametrize("change", BROKEN_PRESETS.values(), ids=BROKEN_PRESETS.keys())
def test_broken_presets_are_rejected(build_preset, change):
    with pytest.raises(ValidationError):
        build_preset(change)
