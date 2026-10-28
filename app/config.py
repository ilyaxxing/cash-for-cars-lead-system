"""Application settings, read from environment variables and an optional .env file.

Everything that differs between clients lives here or in the form preset.
Nothing client-specific is hard-coded anywhere else.
"""

from __future__ import annotations

import base64
import re
import secrets
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.branding.colors import DEFAULT_COLOR, check_color

BASE_DIR = Path(__file__).resolve().parent.parent

# Same shape as the ?src= label: letters, digits, dash and underscore.
SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # A variable declared but left blank in .env or on the hosting panel
        # means "not set", not "set to an empty string".
        env_ignore_empty=True,
    )

    # --- Application ---
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    public_url: str = ""
    secret_key: str = ""
    # Request header that carries the visitor's address, set by the hosting
    # proxy itself (Railway: X-Real-IP). Per-address rate limits key on it.
    # Empty: the connecting address. Never X-Forwarded-For: many proxies pass
    # a client's own value through.
    client_ip_header: str = ""
    # Provided by Railway; used when PUBLIC_URL / GIT_SHA are not set.
    railway_public_domain: str = ""
    railway_git_commit_sha: str = ""
    git_sha: str = ""

    # --- Market and form ---
    preset: str = "us-car-buyout"
    locale: str = "en"
    currency: str = "USD"
    timezone: str = "America/New_York"
    # A client's own form, texts and privacy policy, for a market the shipped
    # files don't cover (docs/customize-the-form.md). Paths like the brand
    # files. PRESET_FILE replaces PRESET. LOCALE_FILE is laid over
    # locales/<LOCALE>.json when that file exists, and is the whole set
    # otherwise. PRIVACY_POLICY_FILE replaces locales/privacy-policy.<LOCALE>.md.
    preset_file: Path | None = None
    locale_file: Path | None = None
    privacy_policy_file: Path | None = None

    # --- Brand ---
    brand_name: str = "Car Buyout"
    brand_phone: str = ""
    # Accent color of buttons, links and the default logo mark, #RRGGBB. It
    # must read on the dark screens; a color that doesn't is refused.
    brand_color: str = DEFAULT_COLOR
    # Image files (PNG, JPEG or WebP), relative to the repository or absolute;
    # see app/branding/assets.py for what each must be. Without them the
    # designs' own mark and photo are shown.
    brand_logo: Path | None = None
    brand_icon: Path | None = None
    brand_photo: Path | None = None
    # The business card's size, as print shops in the client's country know
    # it: 3.5x2in in the US, 90x50mm in Russia, 85x55mm in Europe, or any
    # card from 85x50mm to 92x56mm (91x55mm in Japan).
    card_size: str = "3.5x2in"
    # A font for card text in scripts Geist lacks (Chinese, Korean, Greek...):
    # a static TrueType file, used only by the card command.
    card_font: Path | None = None

    # --- Privacy policy ---
    operator_name: str = ""
    operator_email: str = ""
    operator_address: str = ""
    policy_effective_date: str = ""

    # --- Owner login ---
    owner_password: str = ""

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/carbuyout"

    # --- Photo storage ---
    # local: a folder, for development. volume: the same folder on a disk that
    # survives deploys (deploy/vps). s3: a bucket (Railway).
    storage_backend: Literal["local", "volume", "s3"] = "local"
    local_storage_dir: Path = BASE_DIR / "data" / "uploads"
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    # --- Notifications ---
    # Channels that deliver new leads to the owner, comma-separated.
    notify_channels: Annotated[list[str], NoDecode] = ["push"]
    # Web Push keys, generated once per instance: python -m app.cli vapid-keys
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    # Contact for the push services (mailto: or https:), required by VAPID.
    vapid_subject: str = ""

    # --- Lead sources ---
    # NoDecode: without it pydantic-settings tries to parse the value as JSON
    # and fails on the "id:Label,id:Label" format used in .env.
    source_labels: Annotated[dict[str, str], NoDecode] = {}

    # --- Paths (overridable in tests) ---
    presets_dir: Path = BASE_DIR / "presets"
    locales_dir: Path = BASE_DIR / "locales"
    frontend_dist: Path = BASE_DIR / "frontend" / "dist"

    @property
    def privacy_policy_path(self) -> Path:
        return self.privacy_policy_file or self.locales_dir / f"privacy-policy.{self.locale}.md"

    @field_validator("database_url", mode="before")
    @classmethod
    def _force_asyncpg(cls, value: object) -> object:
        """Point the URL at the asyncpg driver.

        Hosting panels hand out postgresql:// or the legacy postgres:// scheme.
        With those SQLAlchemy picks a synchronous driver and fails on the first
        query, so the scheme is fixed here once instead of by hand on every
        deploy.
        """
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]
        return value

    @field_validator("source_labels", mode="before")
    @classmethod
    def _parse_source_labels(cls, value: object) -> object:
        """Accept "parking:Parking lot,flyer:Flyers"; JSON in .env is awkward."""
        if not isinstance(value, str):
            return value
        labels: dict[str, str] = {}
        for pair in value.split(","):
            if not pair.strip():
                continue
            source, sep, label = pair.partition(":")
            source, label = source.strip(), label.strip()
            if not sep or not label or not SOURCE_ID_RE.match(source):
                raise ValueError(f"SOURCE_LABELS entry {pair.strip()!r} is not id:Label")
            labels[source.lower()] = label
        return labels

    @field_validator("client_ip_header")
    @classmethod
    def _check_client_ip_header(cls, value: str) -> str:
        if value and not re.fullmatch(r"[A-Za-z0-9-]{1,64}", value):
            raise ValueError("CLIENT_IP_HEADER must be a header name such as X-Real-IP")
        if value.lower() == "x-forwarded-for":
            raise ValueError(
                "CLIENT_IP_HEADER cannot be X-Forwarded-For: many proxies pass a "
                "client's own value through"
            )
        return value

    @field_validator("notify_channels", mode="before")
    @classmethod
    def _split_channels(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip().lower() for part in value.split(",") if part.strip()]
        return value

    @field_validator("vapid_public_key")
    @classmethod
    def _check_vapid_public(cls, value: str) -> str:
        # applicationServerKey: an uncompressed P-256 point, 65 bytes starting with 0x04.
        if value and (len(_b64decode(value)) != 65 or _b64decode(value)[0] != 4):
            raise ValueError("VAPID_PUBLIC_KEY is not a base64url P-256 public key")
        return value

    @field_validator("vapid_private_key")
    @classmethod
    def _check_vapid_private(cls, value: str) -> str:
        if value and len(_b64decode(value)) != 32:
            raise ValueError("VAPID_PRIVATE_KEY is not a base64url P-256 private key")
        return value

    @field_validator("vapid_subject")
    @classmethod
    def _check_vapid_subject(cls, value: str) -> str:
        if value and not value.startswith(("mailto:", "https://")):
            raise ValueError("VAPID_SUBJECT must be a mailto: or https:// address")
        return value

    @field_validator("brand_color")
    @classmethod
    def _check_brand_color(cls, value: str) -> str:
        return check_color(value)

    @field_validator(
        "brand_logo",
        "brand_icon",
        "brand_photo",
        "preset_file",
        "locale_file",
        "privacy_policy_file",
        "card_font",
    )
    @classmethod
    def _resolve_client_file(cls, value: Path | None) -> Path | None:
        # Relative to the repository, not to wherever the app was started from.
        if value is None:
            return None
        value = value.expanduser()
        return value if value.is_absolute() else BASE_DIR / value

    @field_validator("card_size")
    @classmethod
    def _check_card_size(cls, value: str) -> str:
        from app.branding.card import CardError, card_format

        try:
            card_format(value)
        except CardError as exc:
            raise ValueError(f"CARD_SIZE: {exc}") from None
        return value

    @field_validator("locale")
    @classmethod
    def _check_locale(cls, value: str) -> str:
        # The language, with its script where it is written in more than one
        # (zh-Hant). The country comes from the form's phone_region: "zh-CN"
        # here would name it twice.
        if not re.fullmatch(r"[a-z]{2,3}(-[A-Z][a-z]{3})?", value):
            raise ValueError(
                f"LOCALE {value!r} must be a language such as en, tr or zh-Hant, "
                "without the country (the form's phone_region gives that)"
            )
        return value

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("CURRENCY must be an ISO 4217 code such as USD")
        return value

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        # Fail at startup rather than show the owner times in the wrong zone.
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"TIMEZONE {value!r} is not a known IANA time zone") from exc
        return value

    @model_validator(mode="after")
    def _check_production(self) -> Settings:
        """In production a missing secret is a startup error, not a runtime surprise."""
        if not self.is_production:
            return self
        problems = []
        if len(self.secret_key) < 32:
            problems.append("SECRET_KEY must be at least 32 characters")
        if not self.owner_password:
            problems.append("OWNER_PASSWORD is required")
        if not self.resolved_public_url.startswith("https://"):
            problems.append("PUBLIC_URL must be an https:// address")
        if not self.operator_name:
            problems.append("OPERATOR_NAME is required for the privacy policy and consent")
        if not self.operator_email:
            problems.append("OPERATOR_EMAIL is required: the privacy policy needs a contact")
        # A container's own disk is wiped on every deploy: photos there would
        # vanish. A bucket (Railway) or a volume (deploy/vps) keeps them.
        if self.storage_backend == "local":
            problems.append("STORAGE_BACKEND must be s3 or volume in production")
        elif self.storage_backend == "s3" and not all(
            (self.s3_bucket, self.s3_access_key_id, self.s3_secret_access_key)
        ):
            problems.append("S3_BUCKET, S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY are required")
        if "push" in self.notify_channels and not (
            self.vapid_public_key and self.vapid_private_key and self.vapid_subject
        ):
            problems.append("VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY and VAPID_SUBJECT are required")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @property
    def push_configured(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def resolved_public_url(self) -> str:
        if self.public_url:
            return self.public_url.rstrip("/")
        if self.railway_public_domain:
            return f"https://{self.railway_public_domain}"
        return ""

    @property
    def version(self) -> str:
        """Commit the running code was built from; deploys wait for it in /healthz."""
        return self.git_sha or self.railway_git_commit_sha or "dev"

    @cached_property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @cached_property
    def signing_key(self) -> bytes:
        """Key for seller tokens and owner sessions.

        Production refuses to start without SECRET_KEY. A development
        instance without one gets a random key per process: tokens stop
        working after a restart, which is harmless locally.
        """
        if self.secret_key:
            return self.secret_key.encode()
        return secrets.token_bytes(32)


def _b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError):
        return b""


@lru_cache
def get_settings() -> Settings:
    return Settings()
