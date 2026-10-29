"""Maintenance commands.

    python -m app.cli vapid-keys               print a new key pair for Web Push
    python -m app.cli qr [--source card]       QR code for business cards and stickers
    python -m app.cli card [--env-file F]      business card to print, with the QR code
    python -m app.cli seed-demo [--count 40]   fill a development database with fake leads

seed-demo generates only fictional data: 555-01xx phone numbers, example.com
addresses, drawn placeholder photos. It refuses to run in production.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import random
import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from app import qr as qr_codes
from app.branding import Brand, BrandError
from app.branding import card as cards
from app.config import Settings, get_settings
from app.db.models import Lead, LeadEvent, Note, Photo
from app.db.session import create_engine, create_session_factory
from app.i18n import LocaleError, load_messages, text_keys, translation_problems
from app.preset.loader import PresetError, check_texts, load_preset
from app.services.images import process_upload
from app.services.leads import apply_status
from app.services.validation import format_phone
from app.storage import create_storage

CARS = [
    ("Toyota", "Camry"), ("Toyota", "RAV4"), ("Ford", "F-150"), ("Ford", "Escape"),
    ("Chevrolet", "Silverado"), ("Honda", "Civic"), ("Honda", "CR-V"), ("Nissan", "Altima"),
    ("Jeep", "Wrangler"), ("Hyundai", "Tucson"), ("Kia", "Sorento"), ("Tesla", "Model 3"),
    ("Subaru", "Outback"), ("Ram", "1500"),
]  # fmt: skip
FIRST = ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Jamie", "Drew"]
LAST = ["Lee", "Parker", "Reed", "Brooks", "Hayes", "Price", "Ellis", "Grant", "Shaw"]
CITIES = [("Austin", "78701"), ("Dallas", "75201"), ("Houston", "77002"), ("San Antonio", "78205")]
SOURCES = ["card", "card", "card", "direct", "flyer", "parking"]
NOTES = [
    "Called the seller, viewing booked for Thursday.",
    "Offered 1,500 under asking; seller is thinking it over.",
    "Asked for photos of the rear bumper scratch.",
    "Agreed on price, paperwork on Saturday.",
]


def placeholder_photo(label: str, hue: int) -> bytes:
    image = Image.new("RGB", (1200, 800), (40 + hue % 60, 46 + hue % 40, 52 + hue % 80))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 560, 1200, 800), fill=(24, 26, 26))
    draw.text((60, 620), label.upper(), fill=(244, 243, 238))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


async def seed_demo(count: int) -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("seed-demo is for development databases only")
    preset = load_preset(settings.presets_dir, settings.preset, settings.preset_file)
    slots = next(f for s in preset.steps for f in s.fields if f.type == "photos").slots
    storage = create_storage(settings)
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    rng = random.Random(7)
    now = datetime.now(UTC)

    async with sessions() as session:
        for index in range(count):
            make, model = rng.choice(CARS)
            city, zip_code = rng.choice(CITIES)
            created = now - timedelta(hours=index * 9 + rng.randint(0, 6))
            year = rng.randint(2008, 2025)
            has_price = rng.random() < 0.7
            lead = Lead(
                make=make,
                model=model,
                year=year,
                mileage=rng.randint(8, 190) * 1000,
                asking_price=rng.randint(30, 400) * 100 if has_price else None,
                location=city,
                name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                phone=f"+1512555{rng.randint(100, 199):04d}",
                source=rng.choice(SOURCES),
                created_at=created,
                status_changed_at=created,
                submitted_at=created,
                preset_id=preset.id,
                answers={
                    "condition": rng.choice(
                        ["excellent", "good", "needs_repairs", "accident_damaged", "not_running"]
                    ),
                    "accident": rng.choice(["no", "no", "yes", "unknown"]),
                    "finance": rng.choice(["no", "no", "yes"]),
                    "postal_code": zip_code,
                    "contact_method": rng.choice(["call", "call", "sms", "whatsapp", "email"]),
                    **(
                        {"vin": f"1HGCM82633A{rng.randint(100000, 999999)}"}
                        if rng.random() < 0.5
                        else {}
                    ),
                    **({"email": f"seller{index}@example.com"} if rng.random() < 0.5 else {}),
                },
            )
            session.add(lead)
            await session.flush()

            # Older leads have been worked on: move them along the statuses.
            path = (
                []
                if index < 6
                else rng.choice(
                    [["in_work"], ["in_work", "bought"], ["rejected"], ["in_work", "rejected"]]
                )
            )
            moment = created
            for status in path:
                moment += timedelta(hours=rng.randint(2, 30))
                previous = lead.status
                apply_status(lead, status, moment)
                session.add(
                    LeadEvent(
                        lead_id=lead.id,
                        kind="status",
                        from_status=previous,
                        to_status=status,
                        created_at=moment,
                    )
                )
            if path and rng.random() < 0.6:
                session.add(Note(lead_id=lead.id, text=rng.choice(NOTES), created_at=moment))

            for position, slot in enumerate(slots[: rng.choice([0, 2, 4, 6])]):
                image = process_upload(
                    placeholder_photo(f"{make} {model} - {slot.id}", index * 13 + position * 7)
                )
                name = secrets.token_hex(16)
                key, thumb = f"leads/{lead.id}/{name}.jpg", f"leads/{lead.id}/{name}-thumb.jpg"
                await storage.put(key, image.full, "image/jpeg")
                await storage.put(thumb, image.thumb, "image/jpeg")
                session.add(
                    Photo(
                        lead_id=lead.id,
                        slot=slot.id,
                        key=key,
                        thumb_key=thumb,
                        width=image.width,
                        height=image.height,
                        size_bytes=len(image.full),
                    )
                )
                lead.has_photos = True
        await session.commit()
    await engine.dispose()
    print(f"Added {count} demo leads.")


def new_vapid_keys() -> dict[str, str]:
    """A P-256 key pair in the base64url form browsers and pywebpush expect."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    return {"VAPID_PUBLIC_KEY": b64(public), "VAPID_PRIVATE_KEY": b64(private)}


def vapid_keys() -> None:
    for name, value in new_vapid_keys().items():
        print(f"{name}={value}")


def qr(
    env_file: Path | None,
    source: str,
    size_mm: float,
    url: str | None,
    out: Path,
    link_only: bool = False,
) -> None:
    # The client's settings file gives the address and the place names, as
    # for the card; it is read as for development, without a database.
    settings = Settings(_env_file=env_file, app_env="development") if env_file else get_settings()
    checked = qr_codes.plan(
        url or settings.resolved_public_url,
        source,
        size_mm=size_mm,
        labels=settings.source_labels,
    )
    for warning in checked.warnings:
        print(f"WARNING: {warning}")
    if checked.problems:
        raise SystemExit("Not written: " + "; ".join(checked.problems))
    print(f"link:    {checked.url}")
    # Maps, social profiles and auto-replies take the link itself: nothing to print.
    if link_only:
        return
    svg, png = qr_codes.write(checked, out)
    side = checked.modules
    print(f"matrix:  {side}x{side}, error correction H, quiet zone {qr_codes.BORDER} modules")
    print(
        f"module:  {checked.module_mm:.2f} mm at {size_mm:g} mm "
        f"(print limit {qr_codes.MIN_MODULE_MM} mm)"
    )
    print(f"print:   {svg}")
    print(f"preview: {png}")


def check_texts_command(env_file: Path | None) -> None:
    """A client's form and texts: every text the form needs, and a full translation."""
    settings = Settings(_env_file=env_file, app_env="development") if env_file else get_settings()
    preset = load_preset(settings.presets_dir, settings.preset, settings.preset_file)
    messages = load_messages(settings.locales_dir, settings.locale, settings.locale_file)
    problems = []
    try:
        check_texts(preset, messages)
    except PresetError as exc:
        problems.append(str(exc))
    reference = load_messages(settings.locales_dir, "en")
    problems += translation_problems(reference, messages)
    if problems:
        raise SystemExit("Texts to fix:\n  " + "\n  ".join(problems))
    count = len(text_keys(messages.data))
    print(f"texts:   {count} in {settings.locale!r}, nothing missing, placeholders as in English")
    print(f"form:    {preset.id}, every question has its texts")


def card(
    env_file: Path | None,
    url: str | None,
    name: str,
    phone: str | None,
    cmyk: str | None,
    size: str | None,
    out: Path,
) -> None:
    # A client's settings file is read as for development: the card needs
    # its brand, not a production database.
    settings = Settings(_env_file=env_file, app_env="development") if env_file else get_settings()
    base_url = url or settings.resolved_public_url
    if not base_url:
        raise SystemExit("No address for the QR code: set PUBLIC_URL or pass --url")
    try:
        brand = Brand.load(settings)
        messages = load_messages(settings.locales_dir, settings.locale, settings.locale_file)
        # The phone reads as people there write it, however it was typed.
        preset = load_preset(settings.presets_dir, settings.preset, settings.preset_file)
        given = settings.brand_phone if phone is None else phone
        text = cards.CardText(
            brand_name=settings.brand_name,
            accent=cards.accent_ink(brand.palette.accent, cmyk),
            base_url=base_url,
            phone=format_phone(given, preset.phone_region),
            name=name,
            logo=cards.logo_image(brand.logo.asset.body) if brand.logo else None,
            texts={
                key: messages.t(f"card.{key}")
                for key in cards.TEXT_KEYS
                if messages.has(f"card.{key}")
            },
            format=cards.card_format(size or settings.card_size),
            font=settings.card_font,
            locale=settings.locale,
        )
        made = cards.make(text)
    except (BrandError, cards.CardError, LocaleError, PresetError) as exc:
        raise SystemExit(f"Not written: {exc}") from None
    for warning in made.warnings:
        print(f"WARNING: {warning}")
    stem = re.sub(r"[^a-z0-9]+", "-", settings.brand_name.lower()).strip("-") or "card"
    paths = cards.save(made, out, stem, f"{settings.brand_name} business card")
    print(f"link:    {made.plan.url}")
    print(f"module:  {made.plan.module_mm:.2f} mm (print limit {qr_codes.MIN_MODULE_MM} mm)")
    print(
        f"accent:  {made.accent.percent()}" + ("" if cmyk else " (converted from the screen color)")
    )
    print(f"size:    {made.format.label}, CMYK, fonts embedded")
    print(f"print:   {paths['pdf']}")
    print(f"marks:   {paths['marks']} (the same with crop marks)")
    print(f"preview: {paths['preview']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("vapid-keys", help="print a new key pair for Web Push")
    code = commands.add_parser("qr", help="QR code, or the link alone, for a place sellers see")
    code.add_argument("--env-file", type=Path, help="the client's settings, e.g. clients/acme.env")
    code.add_argument("--source", default="card", help="placement label; card (default) uses /v")
    code.add_argument(
        "--link-only", action="store_true", help="print the link for an online place, no files"
    )
    code.add_argument(
        "--size-mm",
        type=float,
        default=qr_codes.DEFAULT_SIZE_MM,
        help="printed side of the code without the quiet zone",
    )
    code.add_argument("--url", help="public address, defaults to PUBLIC_URL")
    code.add_argument("--out", type=Path, default=Path("qr"), help="output folder")
    business = commands.add_parser("card", help="business card to print, with the QR code")
    business.add_argument(
        "--env-file", type=Path, help="the client's settings, e.g. clients/acme.env"
    )
    business.add_argument("--url", help="public address, defaults to PUBLIC_URL")
    business.add_argument("--name", default="", help="contact person on the back, optional")
    business.add_argument("--phone", help="phone on the back, defaults to BRAND_PHONE")
    business.add_argument(
        "--cmyk", help="the brand's print color in percent, e.g. 20,0,90,0 (from its brand guide)"
    )
    business.add_argument(
        "--size", help="the country's card size, e.g. 90x55mm; defaults to CARD_SIZE"
    )
    business.add_argument("--out", type=Path, default=Path("cards"), help="output folder")
    texts = commands.add_parser(
        "check-texts", help="a client's form and texts: nothing missing, placeholders intact"
    )
    texts.add_argument("--env-file", type=Path, help="the client's settings, e.g. clients/acme.env")
    seed = commands.add_parser("seed-demo", help="fill a development database with fake leads")
    seed.add_argument("--count", type=int, default=40)
    args = parser.parse_args()
    if args.command == "vapid-keys":
        vapid_keys()
    elif args.command == "qr":
        qr(args.env_file, args.source, args.size_mm, args.url, args.out, args.link_only)
    elif args.command == "card":
        card(args.env_file, args.url, args.name, args.phone, args.cmyk, args.size, args.out)
    elif args.command == "check-texts":
        check_texts_command(args.env_file)
    elif args.command == "seed-demo":
        asyncio.run(seed_demo(args.count))


if __name__ == "__main__":
    main()
