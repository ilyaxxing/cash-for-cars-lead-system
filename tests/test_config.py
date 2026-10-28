import pytest
from pydantic import ValidationError

from tests.conftest import make_settings, vapid_keys

PRODUCTION = {
    "app_env": "production",
    "secret_key": "s" * 48,
    "owner_password": "correct horse battery staple",
    "public_url": "https://buyer.example.com",
    "operator_name": "Example Auto LLC",
    "operator_email": "privacy@example.com",
    "storage_backend": "s3",
    "s3_bucket": "photos",
    "s3_access_key_id": "test-key-id",
    "s3_secret_access_key": "test-secret",
    **vapid_keys(),
}


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("postgresql+asyncpg://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
    ],
)
def test_database_url_is_forced_to_asyncpg(given, expected):
    assert make_settings(database_url=given).database_url == expected


def test_defaults_describe_a_us_instance():
    settings = make_settings()
    assert settings.brand_name == "Car Buyout"
    assert settings.preset == "us-car-buyout"
    assert settings.currency == "USD"
    assert not settings.is_production


def test_blank_environment_values_mean_unset(monkeypatch):
    monkeypatch.setenv("BRAND_NAME", "")
    monkeypatch.setenv("STORAGE_BACKEND", "")
    settings = make_settings()
    assert settings.brand_name == "Car Buyout"
    assert settings.storage_backend == "local"


def test_source_labels_are_parsed_from_pairs():
    settings = make_settings(source_labels="parking:Parking lot, Flyer:Flyers ,")
    assert settings.source_labels == {"parking": "Parking lot", "flyer": "Flyers"}


@pytest.mark.parametrize("value", ["parking", "parking:", "bad id:Label"])
def test_malformed_source_labels_are_rejected(value):
    with pytest.raises(ValidationError, match="SOURCE_LABELS"):
        make_settings(source_labels=value)


def test_unknown_timezone_stops_startup():
    with pytest.raises(ValidationError, match="TIMEZONE"):
        make_settings(timezone="America/Atlantis")


@pytest.mark.parametrize("value", ["en", "tr", "zh-Hant", "fil"])
def test_locale_is_a_language_with_its_script(value):
    assert make_settings(locale=value).locale == value


@pytest.mark.parametrize("value", ["zh-CN", "en_US", "EN", "russian"])
def test_locale_names_no_country(value):
    with pytest.raises(ValidationError, match="LOCALE"):
        make_settings(locale=value)


def test_card_size_is_a_size_print_shops_know():
    assert make_settings(card_size="91x55mm").card_size == "91x55mm"
    with pytest.raises(ValidationError, match="CARD_SIZE"):
        make_settings(card_size="A4")


def test_currency_must_be_an_iso_code():
    with pytest.raises(ValidationError, match="CURRENCY"):
        make_settings(currency="dollars")


def test_complete_production_settings_are_accepted():
    settings = make_settings(**PRODUCTION)
    assert settings.is_production


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("secret_key", "short", "SECRET_KEY"),
        ("owner_password", "", "OWNER_PASSWORD"),
        ("public_url", "http://buyer.example.com", "PUBLIC_URL"),
        ("operator_name", "", "OPERATOR_NAME"),
        ("operator_email", "", "OPERATOR_EMAIL"),
        ("storage_backend", "local", "STORAGE_BACKEND"),
        ("s3_bucket", "", "S3_BUCKET"),
        ("vapid_private_key", "", "VAPID"),
    ],
)
def test_production_refuses_to_start_without(field, value, message):
    with pytest.raises(ValidationError, match=message):
        make_settings(**{**PRODUCTION, field: value})


def test_production_keeps_photos_on_a_volume_without_a_bucket():
    """A server of the client's own (deploy/vps): photos in a Docker volume."""
    settings = make_settings(
        **{**PRODUCTION, "storage_backend": "volume", "s3_bucket": "", "s3_access_key_id": ""}
    )
    assert settings.storage_backend == "volume"


def test_public_url_falls_back_to_railway_domain():
    settings = make_settings(railway_public_domain="buyer-production.up.railway.app")
    assert settings.resolved_public_url == "https://buyer-production.up.railway.app"


def test_version_prefers_explicit_git_sha():
    assert make_settings().version == "dev"
    assert make_settings(railway_git_commit_sha="abc123").version == "abc123"
    assert make_settings(git_sha="def456", railway_git_commit_sha="abc123").version == "def456"
