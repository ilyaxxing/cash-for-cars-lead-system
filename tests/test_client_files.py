"""A client's own form, texts and privacy policy, for a market the shipped files don't cover."""

# Russian text is the point of some of these tests.
# ruff: noqa: RUF001

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from app.config import BASE_DIR
from app.i18n import LocaleError, load_messages
from app.preset.loader import PresetError, check_texts, load_preset
from app.web.privacy import PolicyError, check_policy
from tests.conftest import make_settings
from tests.test_deploy import env_file  # noqa: F401 (fixture)
from tools import deploy

LOCALES = BASE_DIR / "locales"
PRESETS = BASE_DIR / "presets"


def english() -> dict:
    return json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_a_client_file_changes_a_few_texts_of_the_shipped_locale(tmp_path):
    placeholder = "020 7946 0958"  # pii-allow: UK drama range
    extra = write_json(
        tmp_path / "texts.json", {"preset": {"fields": {"phone": {"placeholder": placeholder}}}}
    )
    messages = load_messages(LOCALES, "en", extra)
    assert messages.t("preset.fields.phone.placeholder") == placeholder
    # Everything else is still the shipped text.
    assert messages.t("preset.fields.phone.label") == "Phone number"
    assert messages.t("statuses.bought") == "Purchased"


def test_a_client_file_is_the_whole_set_for_a_language_nothing_ships_for(tmp_path):
    texts = english()
    texts["statuses"]["bought"] = "Куплено"
    extra = write_json(tmp_path / "ru.json", texts)
    messages = load_messages(LOCALES, "ru", extra)
    assert messages.locale == "ru"
    assert messages.t("statuses.bought") == "Куплено"
    check_texts(load_preset(PRESETS, "us-car-buyout"), messages)


def test_a_missing_client_file_is_named(tmp_path):
    with pytest.raises(LocaleError, match="LOCALE_FILE"):
        load_messages(LOCALES, "ru", tmp_path / "nowhere.json")


def test_a_client_preset_file_replaces_the_shipped_one(tmp_path, preset_data):
    preset_data.update(id="ru-car-buyout", distance_unit="km", phone_region="RU")
    preset_data.pop("postal_code_format")
    preset_data["postal_code_pattern"] = r"\d{6}"
    path = tmp_path / "form.yaml"
    path.write_text(yaml.safe_dump(preset_data, allow_unicode=True), encoding="utf-8")
    preset = load_preset(PRESETS, "us-car-buyout", path)
    assert (preset.id, preset.distance_unit, preset.phone_region) == ("ru-car-buyout", "km", "RU")
    with pytest.raises(PresetError, match="PRESET_FILE"):
        load_preset(PRESETS, "us-car-buyout", tmp_path / "nowhere.yaml")


def test_the_app_does_not_start_without_a_privacy_policy(tmp_path):
    check_policy(make_settings())
    with pytest.raises(PolicyError, match="LOCALE='ru'"):
        check_policy(make_settings(locale="ru"))
    with pytest.raises(PolicyError, match="PRIVACY_POLICY_FILE"):
        check_policy(make_settings(privacy_policy_file=tmp_path / "nowhere.md"))


async def test_pages_and_policy_come_in_the_client_language(client_for, tmp_path):
    data = english()
    data["form"]["page_title"] = "Продать машину"
    data["dashboard"]["leads"]["title"] = "Заявки"
    texts = write_json(tmp_path / "ru.json", data)
    policy = tmp_path / "policy.md"
    policy.write_text("# Политика\n\nОператор: {operator}\n", encoding="utf-8")
    client = client_for(
        locale="ru", locale_file=texts, privacy_policy_file=policy, operator_name="ООО Пример"
    )
    form = await client.get("/")
    # The shipped preset is the US one: the country comes from its phone_region.
    assert form.text.startswith('<html lang="ru-US">')
    # The name in a browser tab and on a home screen bookmark.
    assert "<title>Продать машину</title>" in form.text
    assert "<title>Заявки</title>" in (await client.get("/app/")).text
    page = await client.get("/privacy")
    assert page.status_code == 200
    assert 'lang="ru-US"' in page.text
    assert "<h1>Политика</h1>" in page.text


def client_files(tmp_path: Path) -> dict[str, str]:
    """A client's form, texts and policy, as the installer saves them in clients/<id>/."""
    (tmp_path / "form.yaml").write_text((PRESETS / "us-car-buyout.yaml").read_text())
    write_json(tmp_path / "Texts.JSON", {"statuses": {"bought": "Bought"}})
    (tmp_path / "policy.md").write_text("# Privacy\n")
    return {
        "PRESET_FILE": str(tmp_path / "form.yaml"),
        "LOCALE_FILE": str(tmp_path / "Texts.JSON"),
        "PRIVACY_POLICY_FILE": str(tmp_path / "policy.md"),
    }


def test_client_files_go_to_the_app_as_paths_inside_the_upload(env_file, tmp_path):  # noqa: F811
    env = {**deploy.read_env(env_file), **client_files(tmp_path)}
    variables = deploy.railway_variables(env, "abc123")
    assert variables["PRESET_FILE"] == "brand/preset.yaml"
    assert variables["LOCALE_FILE"] == "brand/locale.json"
    assert variables["PRIVACY_POLICY_FILE"] == "brand/privacy-policy.md"
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=BASE_DIR
    ).stdout.strip()
    upload = tmp_path / "upload"
    upload.mkdir()
    deploy.stage(env, sha, upload)
    assert (upload / "brand" / "locale.json").read_text() == (tmp_path / "Texts.JSON").read_text()
    assert (upload / "brand" / "privacy-policy.md").is_file()


def test_a_broken_client_form_stops_the_deploy_before_anything_is_created(env_file, tmp_path):  # noqa: F811
    env = {**deploy.read_env(env_file), **client_files(tmp_path)}
    deploy.fill_secrets(env_file, env)
    deploy.validate(env)
    (tmp_path / "form.yaml").write_text("id: broken\n")
    with pytest.raises(deploy.DeployError, match="The form would not load"):
        deploy.validate(env)


def test_a_translation_is_checked_against_english(tmp_path, capsys):
    from app.cli import check_texts_command
    from app.i18n import Messages, translation_problems

    reference = load_messages(LOCALES, "en")
    full = english()
    assert translation_problems(reference, Messages("ru", full)) == []
    del full["dashboard"]["lead"]["copy"]
    full["form"]["header"]["step"] = "Step {n}"
    assert translation_problems(reference, Messages("ru", full)) == [
        "form.header.step: placeholders should be {n}, {total}",
        "missing: dashboard.lead.copy",
    ]
    texts = write_json(tmp_path / "ru.json", full)
    env = tmp_path / "client.env"
    env.write_text(f"LOCALE=ru\nLOCALE_FILE={texts}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"missing: dashboard\.lead\.copy"):
        check_texts_command(env)
