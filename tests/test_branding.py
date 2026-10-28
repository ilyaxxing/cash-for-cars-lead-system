"""The client's look: accent color, logo, icons and welcome photo (app/branding)."""

import io
import re
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pydantic import ValidationError

from app.branding import Brand, BrandError, Palette, check_color
from app.branding.colors import BACKGROUND, DARK, LIGHT, MIN_CONTRAST, contrast, parse
from app.config import BASE_DIR
from app.main import create_app
from tests.conftest import make_settings

# --- color ---------------------------------------------------------------------------


def test_color_is_normalized():
    assert check_color("ff8a00") == "#FF8A00"
    assert check_color(" #c7f747 ") == "#C7F747"


@pytest.mark.parametrize("value", ["orange", "#FFF", "#GG0000", "rgb(1,2,3)"])
def test_a_value_that_is_not_a_color_is_refused(value):
    with pytest.raises(ValueError, match="BRAND_COLOR must be a color"):
        check_color(value)


@pytest.mark.parametrize("value", ["#003366", "#0000FF", "#222222"])
def test_a_color_too_dark_for_the_screens_is_refused_with_a_lighter_shade(value):
    with pytest.raises(ValueError, match="too dark") as error:
        check_color(value)
    suggestion = re.search(r"for example (#[0-9A-F]{6})", str(error.value)).group(1)
    assert contrast(parse(suggestion), BACKGROUND) >= MIN_CONTRAST
    assert check_color(suggestion) == suggestion


@pytest.mark.parametrize("value", ["#C7F747", "#FFEE00", "#E53935", "#1E88E5", "#8E5CF6"])
def test_text_on_the_accent_is_whichever_of_dark_and_white_reads_better(value):
    palette = Palette.from_hex(value)
    other = LIGHT if palette.on_accent == DARK else DARK
    assert contrast(palette.accent, palette.on_accent) >= contrast(palette.accent, other)


def test_the_color_reaches_every_page_as_css_variables():
    style = Palette.from_hex("#FF8A00").style()
    assert "--accent:#FF8A00" in style
    assert "--accent-rgb:255 138 0" in style
    assert "--on-accent:#111212" in style
    # Doubled: the bundle's own stylesheet comes later in the page.
    assert ":root:root{" in style


def test_settings_check_the_color():
    assert make_settings().brand_color == "#C7F747"
    assert make_settings(brand_color="ff8a00").brand_color == "#FF8A00"
    with pytest.raises(ValidationError, match="too dark"):
        make_settings(brand_color="#001133")


def test_brand_files_are_found_relative_to_the_repository():
    settings = make_settings(brand_logo="clients/acme/logo.png")
    assert settings.brand_logo == BASE_DIR / "clients" / "acme" / "logo.png"
    assert make_settings().brand_logo is None


# --- files ------------------------------------------------------------------------------


def save(image: Image.Image, path: Path, **options) -> Path:
    image.save(path, **options)
    return path


def logo(tmp_path, size=(600, 600), ink=(255, 255, 255, 255), margin=50, name="logo.png"):
    """Light shape on transparency, with empty margins around it."""
    image = Image.new("RGBA", (size[0] + 2 * margin, size[1] + 2 * margin), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((margin, margin, margin + size[0], margin + size[1]), fill=ink)
    return save(image, tmp_path / name)


def photo(tmp_path, size=(2400, 1500), name="photo.jpg"):
    return save(Image.new("RGB", size, (90, 120, 160)), tmp_path / name, quality=85)


def load(**overrides) -> Brand:
    return Brand.load(make_settings(**overrides))


def png_size(body: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(body)).size


def test_without_files_the_designs_own_look_is_used():
    brand = load()
    assert brand.public() == {"logo": None, "photo": None}
    assert brand.files == {}


def test_logo_loses_its_empty_margins_and_is_scaled_for_screens(tmp_path):
    brand = load(brand_logo=logo(tmp_path, size=(1000, 1000)))
    assert (brand.logo.width, brand.logo.height) == (240, 240)
    assert png_size(brand.files["logo.png"].body) == (240, 240)
    assert not brand.logo.wordmark


def test_a_wide_logo_is_a_wordmark(tmp_path):
    brand = load(brand_logo=logo(tmp_path, size=(900, 200)))
    assert brand.logo.wordmark
    assert brand.public()["logo"]["wordmark"] is True


def test_a_dark_logo_is_refused(tmp_path):
    path = logo(tmp_path, ink=(20, 20, 30, 255))
    with pytest.raises(BrandError, match="light version of the logo"):
        load(brand_logo=path)


def test_an_opaque_logo_brings_its_own_background(tmp_path):
    path = save(Image.new("RGB", (400, 400), (10, 10, 10)), tmp_path / "logo.jpg")
    assert load(brand_logo=path).logo.width == 240


def test_a_tiny_logo_is_refused(tmp_path):
    with pytest.raises(BrandError, match="at least 64 px"):
        load(brand_logo=logo(tmp_path, size=(200, 40)))


@pytest.mark.parametrize("setting", ["brand_logo", "brand_icon", "brand_photo"])
def test_a_missing_file_is_named(tmp_path, setting):
    with pytest.raises(BrandError, match=f"{setting.upper()}: .*does not exist"):
        load(**{setting: tmp_path / "nope.png"})


def test_a_file_that_is_not_an_image_is_refused(tmp_path):
    path = tmp_path / "logo.png"
    path.write_text("not an image")
    with pytest.raises(BrandError, match="cannot be read as an image"):
        load(brand_logo=path)


def test_other_image_formats_are_refused(tmp_path):
    path = save(Image.new("RGB", (400, 400), "white"), tmp_path / "logo.gif")
    with pytest.raises(BrandError, match="GIF file; use PNG, JPEG or WebP"):
        load(brand_logo=path)


def test_photo_comes_in_widths_for_phones_and_laptops(tmp_path):
    brand = load(brand_photo=photo(tmp_path))
    assert sorted(brand.photo) == [800, 1536]
    assert png_size(brand.files["photo-800.webp"].body) == (800, 500)
    public = brand.public()["photo"]
    assert public["src"].startswith("/brand/photo-1536.webp?v=")
    small, large = public["srcset"].split(", ")
    assert re.fullmatch(r"/brand/photo-800\.webp\?v=\w+ 800w", small)
    assert re.fullmatch(r"/brand/photo-1536\.webp\?v=\w+ 1536w", large)


def test_a_photo_narrower_than_the_largest_width_is_not_enlarged(tmp_path):
    assert sorted(load(brand_photo=photo(tmp_path, size=(1300, 800))).photo) == [800, 1300]


def test_photo_is_turned_upright_from_its_camera_orientation(tmp_path):
    image = Image.new("RGB", (1500, 2400), (90, 120, 160))
    exif = image.getexif()
    exif[0x0112] = 6  # stored sideways: show rotated 90 degrees
    path = save(image, tmp_path / "photo.jpg", exif=exif)
    assert png_size(load(brand_photo=path).files["photo-800.webp"].body) == (800, 500)


@pytest.mark.parametrize(
    ("size", "message"), [((1000, 600), "at least 1200 px"), ((1600, 1600), "landscape photo")]
)
def test_unsuitable_photos_are_refused(tmp_path, size, message):
    with pytest.raises(BrandError, match=message):
        load(brand_photo=photo(tmp_path, size=size))


# --- icons ------------------------------------------------------------------------------


def center_color(body: bytes) -> tuple[int, int, int]:
    image = Image.open(io.BytesIO(body)).convert("RGB")
    return image.getpixel((image.width // 2 - image.width // 5, image.height // 2))


def test_icons_have_the_sizes_the_phones_ask_for():
    icons = load().icons
    sizes = {name: png_size(asset.body) for name, asset in icons.items()}
    assert sizes == {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "maskable-512.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
        "badge-96.png": (96, 96),
    }
    # iOS fills transparent corners with black: the touch icon is opaque.
    assert Image.open(io.BytesIO(icons["apple-touch-icon.png"].body)).mode == "RGB"


def test_without_an_icon_the_mark_is_drawn_in_the_brand_color():
    body = load(brand_color="#FF8A00").icons["icon-512.png"].body
    assert center_color(body) == (255, 138, 0)


def test_a_square_logo_becomes_the_icon(tmp_path):
    body = load(brand_logo=logo(tmp_path, ink=(255, 0, 0, 255))).icons["icon-512.png"].body
    assert center_color(body) == (255, 0, 0)


def test_a_wordmark_is_not_squeezed_into_the_icon(tmp_path):
    brand = load(brand_color="#FF8A00", brand_logo=logo(tmp_path, size=(900, 200)))
    assert center_color(brand.icons["icon-512.png"].body) == (255, 138, 0)


def test_an_icon_file_wins_over_the_logo(tmp_path):
    icon = logo(tmp_path, ink=(0, 200, 0, 255), name="icon.png")
    brand = load(brand_logo=logo(tmp_path, ink=(255, 0, 0, 255)), brand_icon=icon)
    assert center_color(brand.icons["icon-512.png"].body) == (0, 200, 0)


def test_a_small_icon_file_is_refused(tmp_path):
    with pytest.raises(BrandError, match="at least 192 px"):
        load(brand_icon=logo(tmp_path, size=(120, 120)))


# --- serving ----------------------------------------------------------------------------


async def test_pages_carry_the_color_and_the_files(client_for, tmp_path):
    client = client_for(
        brand_color="#FF8A00", brand_logo=logo(tmp_path), brand_photo=photo(tmp_path)
    )
    for path in ("/", "/app/"):
        html = (await client.get(path)).text
        assert '<style id="brand-colors">:root:root{--accent:#FF8A00' in html
        assert html.index("brand-colors") < html.index('id="app-config"')
    from tests.test_web import embedded_config

    brand = embedded_config(html)["brand"]
    assert brand["logo"]["url"].startswith("/brand/logo.png?v=")
    assert brand["photo"]["src"].startswith("/brand/photo-1536.webp?v=")


async def test_brand_files_are_cached_for_good_only_at_their_versioned_address(
    client_for, tmp_path
):
    client = client_for(brand_logo=logo(tmp_path))
    app_brand = client._transport.app.state.brand
    versioned = await client.get(app_brand.url("logo.png"))
    assert versioned.status_code == 200
    assert versioned.headers["content-type"] == "image/png"
    assert "immutable" in versioned.headers["cache-control"]
    plain = await client.get("/brand/logo.png")
    assert plain.headers["cache-control"] == "public, max-age=3600"
    assert (await client.get("/brand/other.png")).status_code == 404


async def test_manifest_icons_are_versioned_and_served(client_for):
    client = client_for(brand_color="#FF8A00")
    manifest = (await client.get("/app/manifest.webmanifest")).json()
    for icon in manifest["icons"]:
        assert "?v=" in icon["src"]
        response = await client.get(icon["src"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
    assert (await client.get("/app/icons/unknown.png")).status_code == 404


def test_a_broken_brand_file_stops_the_start(tmp_path, frontend_dist):
    path = tmp_path / "logo.png"
    path.write_text("not an image")
    with pytest.raises(BrandError):
        create_app(make_settings(frontend_dist=frontend_dist, brand_logo=path))
