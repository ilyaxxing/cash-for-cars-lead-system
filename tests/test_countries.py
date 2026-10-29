"""Every country in countries/: starting files that work, and a demo that holds together."""

import re
from typing import Any

import pytest
import yaml
from dotenv import dotenv_values

from app.config import BASE_DIR
from app.i18n import load_messages, translation_problems
from app.preset.loader import check_texts, load_preset
from app.web.privacy import check_policy
from tests.conftest import make_settings
from tools import make_buyer_site
from tools.make_demo import DEFAULT, SETTINGS
from tools.pii_scan import scan_line

COUNTRIES = BASE_DIR / "countries"
CODES = sorted(path.name for path in COUNTRIES.iterdir() if path.is_dir())
# What tools/make_demo.py and frontend/src/demo/seed.ts read from demo.yaml.
DEMO_KEYS = {
    "label",
    "lang",
    "business",
    "calls_off",
    "policy_note",
    "price_scale",
    "price_step",
    "featured",
    "phones",
    "cars",
    "names",
    "cities",
    "page",
}


def settings_of(code: str) -> dict[str, Any]:
    """The country's settings.env, as overrides for the test settings."""
    values = dotenv_values(COUNTRIES / code / "settings.env")
    return {key.lower(): value for key, value in values.items()}


def demo_of(code: str) -> dict[str, Any]:
    return yaml.safe_load((COUNTRIES / code / "demo.yaml").read_text(encoding="utf-8"))


def test_the_countries_are_there():
    assert DEFAULT in CODES
    assert len(CODES) >= 11


@pytest.mark.parametrize("code", CODES)
def test_a_country_has_its_files(code):
    folder = COUNTRIES / code
    assert (folder / "settings.env").is_file()
    assert (folder / "demo.yaml").is_file()
    overrides = settings_of(code)
    for key in ("locale_file", "preset_file", "privacy_policy_file"):
        if key in overrides:
            assert (BASE_DIR / overrides[key]).is_file(), f"{code}: {key}"
    # A language nothing ships for needs its whole set of texts and a policy.
    if overrides["locale"] != "en":
        assert "locale_file" in overrides and "privacy_policy_file" in overrides


@pytest.mark.parametrize("code", CODES)
def test_a_country_has_every_text_its_form_needs(code):
    settings = make_settings(**settings_of(code))
    preset = load_preset(settings.presets_dir, settings.preset, settings.preset_file)
    messages = load_messages(settings.locales_dir, settings.locale, settings.locale_file)
    check_texts(preset, messages)
    assert translation_problems(load_messages(settings.locales_dir, "en"), messages) == []
    check_policy(settings)


@pytest.mark.parametrize("code", CODES)
async def test_a_country_pages_come_in_its_language(client_for, code):
    overrides = settings_of(code)
    business = demo_of(code)["business"]
    client = client_for(**overrides, **{key: business[key] for key in SETTINGS})
    form = await client.get("/")
    assert form.status_code == 200
    assert f'<html lang="{overrides["locale"]}-' in form.text
    policy = await client.get("/privacy")
    assert policy.status_code == 200
    # Every placeholder in the policy was known and filled in.
    assert not re.search(r"\{[a-z_]+\}", policy.text)
    assert business["operator_name"] in policy.text


@pytest.mark.parametrize("code", CODES)
def test_a_country_demo_is_complete(code):
    demo = demo_of(code)
    assert demo.keys() >= DEMO_KEYS
    assert demo["business"].keys() >= {*SETTINGS, "card_contact"}
    assert len(demo["featured"]) == 6
    assert demo["phones"] and demo["cars"] and demo["names"] and demo["cities"]
    # Built and committed: tools/make_demo.py ran after the country changed.
    demo_dir = BASE_DIR / "docs" / "demo" if code == DEFAULT else BASE_DIR / "docs" / "demo" / code
    card_dir = BASE_DIR / "docs" / "assets" / "card" / ("" if code == DEFAULT else code)
    assert (demo_dir / "index.html").is_file() and (demo_dir / "app" / "index.html").is_file()
    assert (card_dir / "lime-front.webp").is_file()


@pytest.mark.parametrize("code", CODES)
def test_a_country_page_for_buyers_fills_the_template(code):
    page = make_buyer_site.page(code)
    assert "{{" not in page
    assert f'<html lang="{demo_of(code)["lang"]}">' in page


@pytest.mark.parametrize("code", CODES)
def test_a_country_demo_phones_are_fictional(code):
    """The demo shows its numbers to strangers: none may belong to a real person."""
    for phone in demo_of(code)["phones"]:
        assert phone.startswith("+"), phone
        assert list(scan_line(phone)) == [], phone


def test_the_link_maker_offers_every_country():
    page = (BASE_DIR / "docs" / "index.html").read_text(encoding="utf-8")
    select = page[page.index('<select id="maker-country">') : page.index("</select>")]
    options = re.findall(r'<option value="([a-z-]+)">([^<]+)</option>', select)
    assert sorted(code for code, _ in options) == CODES
    assert options[0][0] == DEFAULT
    for code, label in options:
        assert label == demo_of(code)["label"]


def test_the_demo_builder_finds_every_country():
    from tools.make_demo import country_codes

    assert country_codes()[0] == DEFAULT
    assert sorted(country_codes()) == CODES
