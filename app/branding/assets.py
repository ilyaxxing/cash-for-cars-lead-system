"""The client's logo, home-screen icons and welcome photo.

BRAND_LOGO, BRAND_ICON and BRAND_PHOTO name image files (PNG, JPEG or WebP).
They are checked and prepared once, when the app starts: a file that would
look broken stops the start with a message that says what to fix, and
tools/deploy.py runs the same checks before it uploads anything. Without
them the app shows the designs' own mark and photo, in BRAND_COLOR.

Prepared files are kept in memory and served at addresses that carry a hash
of their content, so browsers can cache them for good and a new logo still
shows up at once.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageOps

from app.branding.colors import BACKGROUND, Palette, contrast
from app.branding.mark import badge, mark_icon

if TYPE_CHECKING:
    from app.config import Settings

FORMATS = {"PNG", "JPEG", "WEBP"}
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 60_000_000

# The logo is shown at most about 60 px high; four times that stays sharp.
LOGO_BOX = (1200, 240)
MIN_LOGO_HEIGHT = 64
# A logo this many times wider than tall is a wordmark: it already carries
# the name, so it stands alone instead of beside the name, and it is too
# wide for a square icon.
WORDMARK_RATIO = 1.8
# Smallest side of an image that may become the home-screen icon.
MIN_ICON_SIDE = 192
# A transparent logo sits on the dark screens directly. Ink that barely
# differs from the background disappears; this much of it is too much.
HIDDEN_CONTRAST = 1.6
MAX_HIDDEN_SHARE = 0.4

# The welcome photo: shown full width, up to about 1200 px on a laptop.
PHOTO_WIDTHS = (800, 1536)
MIN_PHOTO_WIDTH = 1200
MIN_PHOTO_RATIO = 1.25

# Home-screen icons: name -> (size, maskable). Android crops maskable icons
# to a circle or a squircle, so their content stays in the middle.
ICONS = {
    "icon-192.png": (192, False),
    "icon-512.png": (512, False),
    "maskable-512.png": (512, True),
    "apple-touch-icon.png": (180, False),
}
BADGE = "badge-96.png"
# The dashboard's background, behind the mark and transparent icons.
ICON_BACKGROUND = (11, 12, 12)
MARK_SHARE = {False: 0.58, True: 0.46}
# Width share of a transparent icon image, and of an opaque one (whose own
# background fills the rest).
TRANSPARENT_SHARE = {False: 0.72, True: 0.56}
OPAQUE_SHARE = {False: 1.0, True: 0.8}


class BrandError(ValueError):
    """A brand file that would look broken; the message says what to do."""


@dataclass(frozen=True)
class Asset:
    body: bytes
    media_type: str
    version: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "version", hashlib.sha256(self.body).hexdigest()[:12])


@dataclass(frozen=True)
class Logo:
    asset: Asset
    width: int
    height: int

    @property
    def wordmark(self) -> bool:
        return self.width >= WORDMARK_RATIO * self.height


def encode(image: Image.Image, kind: str) -> Asset:
    buffer = io.BytesIO()
    if kind == "png":
        image.save(buffer, "PNG", optimize=True)
        return Asset(buffer.getvalue(), "image/png")
    image.save(buffer, "WEBP", quality=82, method=6)
    return Asset(buffer.getvalue(), "image/webp")


def open_image(path: Path, setting: str) -> Image.Image:
    """The file as RGBA, upright, or a BrandError naming the setting."""
    if not path.is_file():
        raise BrandError(f"{setting}: {path} does not exist")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise BrandError(f"{setting}: {path.name} is over {MAX_FILE_BYTES // 2**20} MB")
    try:
        with Image.open(path) as image:
            if image.format not in FORMATS:
                raise BrandError(
                    f"{setting}: {path.name} is a {image.format} file; use PNG, JPEG or WebP"
                )
            if image.width * image.height > MAX_PIXELS:
                raise BrandError(f"{setting}: {path.name} is too large ({image.size}) to process")
            image.load()
            upright = ImageOps.exif_transpose(image)
            return upright.convert("RGBA")
    except BrandError:
        raise
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise BrandError(f"{setting}: {path.name} cannot be read as an image") from exc


def transparent(image: Image.Image) -> bool:
    low, _ = image.getchannel("A").getextrema()
    return low < 250


def trim(image: Image.Image, setting: str, name: str) -> Image.Image:
    """Crop away fully transparent margins, so the logo sits where it is placed."""
    box = image.getchannel("A").point(lambda alpha: 255 if alpha > 8 else 0).getbbox()
    if box is None:
        raise BrandError(f"{setting}: {name} is empty: every pixel is transparent")
    return image.crop(box)


def check_visible(image: Image.Image, setting: str, name: str) -> None:
    sample = image.copy()
    sample.thumbnail((160, 160))
    alpha = sample.getchannel("A").tobytes()
    rgb = sample.convert("RGB").tobytes()
    visible = [tuple(rgb[i * 3 : i * 3 + 3]) for i, a in enumerate(alpha) if a > 128]
    hidden = sum(contrast(pixel, BACKGROUND) < HIDDEN_CONTRAST for pixel in visible)  # type: ignore[arg-type]
    if visible and hidden / len(visible) > MAX_HIDDEN_SHARE:
        raise BrandError(
            f"{setting}: {name} is mostly dark and would disappear on the app's dark "
            "screens. Use a light version of the logo (white or light lettering), the "
            "kind made for dark backgrounds"
        )


def border_color(image: Image.Image) -> tuple[int, int, int]:
    """Average color along the edges: the background an opaque image extends into."""
    small = image.convert("RGB").resize((32, 32), Image.Resampling.BOX)
    pixels = small.tobytes()
    edge = [
        pixels[(y * 32 + x) * 3 : (y * 32 + x) * 3 + 3]
        for y in range(32)
        for x in range(32)
        if x in (0, 31) or y in (0, 31)
    ]
    return tuple(round(sum(p[c] for p in edge) / len(edge)) for c in range(3))  # type: ignore[return-value]


def open_trimmed(path: Path, setting: str) -> Image.Image:
    """The image without its empty margins, checked to show on the dark screens.

    Whether it is see-through is judged before trimming: a dark badge with
    transparent corners is opaque once trimmed, but it still sits on the
    dark background.
    """
    image = open_image(path, setting)
    see_through = transparent(image)
    image = trim(image, setting, path.name)
    if see_through:
        check_visible(image, setting, path.name)
    return image


def load_logo(path: Path) -> tuple[Logo, Image.Image]:
    """The prepared logo, and the full-size trimmed image for the icons."""
    image = open_trimmed(path, "BRAND_LOGO")
    if image.height < MIN_LOGO_HEIGHT:
        raise BrandError(
            f"BRAND_LOGO: {path.name} is {image.height} px tall without its empty "
            f"margins; it needs at least {MIN_LOGO_HEIGHT} px or it looks blurry. "
            "Ask for a larger file"
        )
    shown = image.copy()
    shown.thumbnail(LOGO_BOX, Image.Resampling.LANCZOS)
    return Logo(encode(shown, "png"), shown.width, shown.height), image


def load_icon(path: Path) -> Image.Image:
    image = open_trimmed(path, "BRAND_ICON")
    if min(image.size) < MIN_ICON_SIDE:
        raise BrandError(
            f"BRAND_ICON: {path.name} is {image.width}x{image.height} px; a home-screen "
            f"icon needs at least {MIN_ICON_SIDE} px on each side (512x512 is best)"
        )
    return image


def load_photo(path: Path) -> dict[int, Asset]:
    image = open_image(path, "BRAND_PHOTO")
    if image.width < MIN_PHOTO_WIDTH:
        raise BrandError(
            f"BRAND_PHOTO: {path.name} is {image.width} px wide; it needs at least "
            f"{MIN_PHOTO_WIDTH} px or it looks blurry on a laptop"
        )
    if image.width < MIN_PHOTO_RATIO * image.height:
        raise BrandError(
            f"BRAND_PHOTO: {path.name} is {image.width}x{image.height} px; use a landscape "
            "photo (wider than tall, 3:2 or wider): the welcome screen shows a wide strip"
        )
    flat = Image.new("RGB", image.size, BACKGROUND)
    flat.paste(image, mask=image.getchannel("A"))
    # Never enlarged: a narrower photo is served at its own width instead.
    largest = min(flat.width, PHOTO_WIDTHS[-1])
    widths = sorted({w for w in PHOTO_WIDTHS if w < largest} | {largest})
    photo = {}
    for width in widths:
        height = round(flat.height * width / flat.width)
        photo[width] = encode(flat.resize((width, height), Image.Resampling.LANCZOS), "webp")
    return photo


def icon_from_image(source: Image.Image, size: int, maskable: bool) -> Image.Image:
    if transparent(source):
        background, share = ICON_BACKGROUND, TRANSPARENT_SHARE[maskable]
    else:
        background, share = border_color(source), OPAQUE_SHARE[maskable]
    canvas = Image.new("RGBA", (size, size), (*background, 255))
    box = round(size * share)
    fitted = ImageOps.contain(source, (box, box), Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
    return canvas.convert("RGB")


class Brand:
    """Everything that makes an instance look like the client's own."""

    def __init__(
        self,
        palette: Palette,
        logo: Logo | None = None,
        photo: dict[int, Asset] | None = None,
        icon_source: Image.Image | None = None,
    ) -> None:
        self.palette = palette
        self.logo = logo
        self.photo = photo or {}
        self.icon_source = icon_source
        self.files: dict[str, Asset] = {}
        if logo:
            self.files["logo.png"] = logo.asset
        for width, asset in self.photo.items():
            self.files[f"photo-{width}.webp"] = asset

    @classmethod
    def load(cls, settings: Settings) -> Brand:
        """Check and prepare the brand files named in the settings."""
        logo = icon_source = None
        if settings.brand_logo:
            logo, image = load_logo(settings.brand_logo)
            # A roughly square logo doubles as the icon; a wordmark would be
            # unreadable at icon size, so the mark is used instead.
            if not logo.wordmark and min(image.size) >= MIN_ICON_SIDE:
                icon_source = image
        if settings.brand_icon:
            icon_source = load_icon(settings.brand_icon)
        photo = load_photo(settings.brand_photo) if settings.brand_photo else None
        return cls(Palette.from_hex(settings.brand_color), logo, photo, icon_source)

    @cached_property
    def icons(self) -> dict[str, Asset]:
        """Drawn on first use: a few hundred milliseconds the tests need not pay."""
        palette = self.palette
        icons = {}
        for name, (size, maskable) in ICONS.items():
            if self.icon_source is not None:
                image = icon_from_image(self.icon_source, size, maskable)
            else:
                image = mark_icon(
                    size, MARK_SHARE[maskable], ICON_BACKGROUND, palette.accent, palette.on_accent
                )
            icons[name] = encode(image, "png")
        icons[BADGE] = encode(badge(96), "png")
        return icons

    def url(self, name: str) -> str:
        asset = self.files[name]
        return f"/brand/{name}?v={asset.version}"

    def icon_url(self, name: str) -> str:
        return f"/app/icons/{name}?v={self.icons[name].version}"

    def public(self) -> dict[str, Any]:
        """What the pages need: where the logo and the photo are, if there are any."""
        logo = None
        if self.logo:
            logo = {
                "url": self.url("logo.png"),
                "width": self.logo.width,
                "height": self.logo.height,
                "wordmark": self.logo.wordmark,
            }
        photo = None
        if self.photo:
            sources = [(self.url(f"photo-{width}.webp"), width) for width in sorted(self.photo)]
            photo = {
                "src": sources[-1][0],
                "srcset": ", ".join(f"{url} {width}w" for url, width in sources),
            }
        return {"logo": logo, "photo": photo}
