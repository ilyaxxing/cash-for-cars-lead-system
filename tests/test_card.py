"""The printable business card (app/branding/card.py, python -m app.cli card)."""

import base64
import re
import zlib
from pathlib import Path

import pytest
from PIL import Image

from app import qr as qr_codes
from app.branding import card as cards
from app.branding.colors import parse
from app.cli import card as card_command
from app.config import BASE_DIR
from app.i18n import load_messages

URL = "https://buy.lonestarcars.example"


def texts() -> dict[str, str]:
    messages = load_messages(BASE_DIR / "locales", "en")
    return {key: messages.t(f"card.{key}") for key in cards.TEXT_KEYS}


def card_text(**overrides) -> cards.CardText:
    values = {
        "brand_name": "Lone Star Cars",
        "accent": cards.accent_ink(parse("#FF8A00")),
        "base_url": URL,
        "phone": "(512) 555-0142",
        "name": "Mike Alvarez",
        "texts": texts(),
        **overrides,
    }
    return cards.CardText(**values)


def logo(size=(600, 600)) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.paste((255, 255, 255, 255), (50, 50, size[0] - 50, size[1] - 50))
    return image


@pytest.fixture(scope="module")
def made() -> cards.Card:
    return cards.make(card_text())


def runs(card: cards.Card) -> list[cards.Run]:
    return [op for side in (card.front, card.back) for op in side if isinstance(op, cards.Run)]


def test_every_card_text_is_in_the_locale():
    messages = load_messages(BASE_DIR / "locales", "en")
    assert all(messages.has(f"card.{key}") for key in cards.TEXT_KEYS)


def test_each_size_is_what_print_shops_there_expect():
    mm = 72 / 25.4
    us, ru, eu = (cards.FORMATS[name] for name in ("3.5x2in", "90x50mm", "85x55mm"))
    assert (us.trim, us.page) == ((3.5 * 72, 2 * 72), (3.75 * 72, 2.25 * 72))
    assert ru.page == pytest.approx((94 * mm, 54 * mm))
    assert eu.page == pytest.approx((91 * mm, 61 * mm))
    japan = cards.card_format("91x55mm")
    assert japan.page == pytest.approx((97 * mm, 61 * mm))


@pytest.mark.parametrize("value", ["84x55mm", "90x57mm", "4x2in", "90 x 55 mm", "big"])
def test_a_card_size_outside_the_range_is_refused(value):
    with pytest.raises(cards.CardError, match="85x50mm to 92x56mm"):
        cards.card_format(value)


# Named sizes, and the corners of the metric range.
SIZES = [*cards.FORMATS, "85x50mm", "92x50mm", "92x56mm", "91x55mm", "90x54mm"]


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize(
    "variant",
    [{}, {"logo": logo()}, {"logo": logo((1400, 300))}, {"name": "", "phone": ""}],
    ids=["mark", "square logo", "wordmark", "no contact"],
)
def test_no_text_is_small_or_near_the_cut(variant, size):
    fmt = cards.card_format(size)
    card = cards.make(card_text(format=fmt, **variant))
    assert_inside(card)


def assert_inside(card: cards.Card) -> None:
    fmt = card.format
    safe = fmt.bleed + 9  # 0.125 in inside the trim line
    page_width, page_height = fmt.page
    for run in runs(card):
        assert run.size >= cards.MIN_TEXT, run.text
        width = cards.text_width(run.text, run.face, run.size, run.tracking)
        assert run.x >= safe and run.x + width <= page_width - safe, run.text
        # Capitals above, descenders below the baseline.
        assert run.baseline - cards.rise(run.text, run.face, run.size) >= safe, run.text
        assert run.baseline + 0.25 * run.size <= page_height - safe, run.text


def test_small_gray_text_is_black_ink_only(made):
    for run in runs(made):
        if run.size < 9 and run.ink not in (cards.CREAM, cards.BLACK, cards.PAPER, made.accent):
            assert run.ink.cmyk[:3] == (0, 0, 0), run.text


def test_inks_stay_under_the_total_ink_limit(made):
    inks = {op.ink for side in (made.front, made.back) for op in side if hasattr(op, "ink")}
    assert all(ink.coverage <= cards.TOTAL_INK_LIMIT for ink in inks)


def test_the_background_runs_into_the_bleed(made):
    for side in (made.front, made.back):
        first = side[0]
        assert (first.x, first.y, first.w, first.h) == (0, 0, *made.format.page)


def test_both_sides_carry_the_code_and_the_back_no_address(made):
    codes = [
        next(op for op in side if isinstance(op, cards.Modules)) for side in (made.front, made.back)
    ]
    assert codes[0].matrix == codes[1].matrix
    assert codes[0].module == codes[1].module
    assert not any("lonestarcars" in run.text for run in runs(made))


def test_the_code_is_black_on_white_with_its_quiet_zone(made):
    code = next(op for op in made.front if isinstance(op, cards.Modules))
    plate = next(op for op in made.front if isinstance(op, cards.Box) and op.ink is cards.PAPER)
    assert code.matrix == [[bool(c) for c in row] for row in qr_codes.code(f"{URL}/v").matrix]
    assert code.ink.cmyk == (0, 0, 0, 1)
    margin = code.x - plate.x
    assert margin >= qr_codes.BORDER * code.module - 1e-9
    assert made.plan.url == f"{URL}/v"
    assert made.plan.module_mm >= qr_codes.MIN_MODULE_MM


def test_black_on_the_accent_overprints():
    lime = cards.make(card_text(accent=cards.accent_ink(parse("#C7F747"))))
    on_band = [run for run in lime.back if isinstance(run, cards.Run) and run.ink is cards.BLACK]
    assert on_band and all(run.overprint for run in on_band)


def test_white_on_a_darker_accent_knocks_out():
    purple = cards.make(card_text(accent=cards.accent_ink(parse("#8E5CF6"))))
    band = [run for run in purple.back if isinstance(run, cards.Run) and run.ink is cards.PAPER]
    assert band and not any(run.overprint for run in band)


def test_a_brands_own_cmyk_is_used_as_given():
    ink = cards.accent_ink(parse("#FF8A00"), "0, 50, 100, 0")
    assert ink.cmyk == (0, 0.5, 1, 0)
    assert ink.percent() == "C0 M50 Y100 K0"


@pytest.mark.parametrize("value", ["0,50,100", "a,b,c,d", "0,50,120,0"])
def test_unusable_cmyk_is_refused(value):
    with pytest.raises(cards.CardError, match="four percentages"):
        cards.parse_cmyk(value)


def test_screen_colors_convert_with_black_for_gray():
    assert cards.cmyk_for((255, 255, 255)) == (0, 0, 0, 0)
    assert cards.cmyk_for((0, 0, 0)) == (0, 0, 0, 1)
    assert cards.cmyk_for((255, 138, 0)) == (0, 0.46, 1, 0)


def test_a_logo_is_laid_onto_the_background_in_cmyk():
    image = Image.new("RGBA", (2, 1))
    image.putpixel((0, 0), (255, 255, 255, 255))
    image.putpixel((1, 0), (0, 0, 0, 0))
    flat = cards.logo_in_cmyk(image, cards.BACKGROUND)
    assert flat.mode == "CMYK"
    assert flat.getpixel((0, 0)) == (0, 0, 0, 0)
    assert flat.getpixel((1, 0)) == tuple(round(255 * v) for v in cards.BACKGROUND.cmyk)


def test_text_too_long_to_print_legibly_is_refused():
    item = "Still financed, leased, with liens, past due, or with any other paperwork problem"
    with pytest.raises(cards.CardError, match=r"card\.back_list_2 is too long"):
        cards.make(card_text(texts={**texts(), "back_list_2": item}))


def test_a_railway_address_is_refused():
    with pytest.raises(cards.CardError, match="client's own domain"):
        cards.make(card_text(base_url="https://app-production.up.railway.app"))


def test_an_address_that_is_not_https_is_refused():
    with pytest.raises(cards.CardError, match="https"):
        cards.make(card_text(base_url="http://example.com"))


def pdf_content(path: Path) -> tuple[bytes, bytes]:
    """The file, and its page drawing streams decompressed."""
    data = path.read_bytes()
    streams = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = match.group(1).strip()
        if raw.endswith(b"~>"):  # ASCII85 around the compressed drawing
            raw = base64.a85decode(raw.removesuffix(b"~>"))
        try:
            stream = zlib.decompressobj().decompress(raw)
        except zlib.error:
            continue
        # Drawing instructions are text; embedded fonts are binary.
        if stream.isascii():
            streams.append(stream)
    return data, b"\n".join(streams)


def test_the_command_writes_print_ready_pdfs_and_a_preview(tmp_path, capsys):
    env = tmp_path / "acme.env"
    env.write_text(
        "BRAND_NAME=Acme Auto Buyers\nBRAND_PHONE=(512) 555-0100\n"
        f"BRAND_COLOR=#FFEE00\nPUBLIC_URL={URL}\n",
        encoding="utf-8",
    )
    card_command(env, None, "Mike", None, None, None, tmp_path / "cards")
    folder = tmp_path / "cards"
    assert sorted(path.name for path in folder.iterdir()) == [
        "acme-auto-buyers-crop-marks.pdf",
        "acme-auto-buyers-preview.png",
        "acme-auto-buyers.pdf",
    ]
    data, content = pdf_content(folder / "acme-auto-buyers.pdf")
    assert data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") == 2
    assert data.count(b"/MediaBox [ 0 0 270 162 ]") == 2
    assert data.count(b"/TrimBox [ 9 9 261 153 ]") == 2
    assert data.count(b"/BleedBox [ 0 0 270 162 ]") == 2
    # Fonts embedded; every color CMYK, none RGB.
    assert b"/FontFile2" in data
    assert b"/DeviceRGB" not in data
    assert not re.search(rb"(?<![A-Za-z])(rg|RG)(?![A-Za-z])", content)
    assert re.search(rb"(?<![A-Za-z])k(?![A-Za-z])", content)

    marks, _ = pdf_content(folder / "acme-auto-buyers-crop-marks.pdf")
    assert b"/TrimBox [ 33 33 285 177 ]" in marks
    out = capsys.readouterr().out
    assert "link:    https://buy.lonestarcars.example/v" in out
    assert "accent:  C0 M7 Y100 K0 (converted from the screen color)" in out


def test_the_card_comes_in_the_client_country_size(tmp_path):
    env = tmp_path / "acme.env"
    env.write_text(f"BRAND_NAME=Acme\nCARD_SIZE=90x50mm\nPUBLIC_URL={URL}\n", encoding="utf-8")
    card_command(env, None, "", None, None, None, tmp_path / "ru")
    data, _ = pdf_content(tmp_path / "ru" / "acme.pdf")
    # 94 x 54 mm pages, the 90 x 50 mm card 2 mm inside them.
    assert data.count(b"/MediaBox [ 0 0 266.4567 153.0709 ]") == 2
    assert data.count(b"/TrimBox [ 5.669291 5.669291 260.7874 147.4016 ]") == 2
    card_command(env, None, "", None, None, "85x55mm", tmp_path / "eu")
    data, _ = pdf_content(tmp_path / "eu" / "acme.pdf")
    assert data.count(b"/MediaBox [ 0 0 257.9528 172.9134 ]") == 2


def test_the_command_needs_an_address(tmp_path):
    env = tmp_path / "acme.env"
    env.write_text("BRAND_NAME=Acme\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="No address"):
        card_command(env, None, "", None, None, None, tmp_path / "cards")


# --- other languages and scripts --------------------------------------------------


CHINESE = {
    "front_hot": "高价收购",
    "front_rest": "各种二手车",
    "front_tag_1": "贷款车",
    "front_tag_2": "事故车",
    "front_tag_3": "不能开",
    "cta": "立即估价",
    "scan": "用相机扫一扫",
    "back_title_1": "今天就卖掉您的车",
    "back_title_2": "任何车况都收",
    "back_list_1": "事故车或不能开的车",
    "back_list_2": "还有贷款",
    "back_list_3": "高里程任何年份",
}


def own_font(path: Path, chars: str, variable: bool = False) -> Path:
    """A TrueType font with a tall box for each of `chars`, like ideographs."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    def box():
        pen = TTGlyphPen(None)
        for x, y in ((50, -100), (50, 860), (950, 860), (950, -100)):
            (pen.lineTo if pen.points else pen.moveTo)((x, y))
        pen.closePath()
        return pen.glyph()

    names = {ord(char): f"uni{ord(char):04X}" for char in sorted(set(chars))}
    order = [".notdef", "space", *names.values()]
    font = FontBuilder(1000, isTTF=True)
    font.setupGlyphOrder(order)
    font.setupCharacterMap({32: "space", **names})
    font.setupGlyf({name: TTGlyphPen(None).glyph() if name == "space" else box() for name in order})
    font.setupHorizontalMetrics({name: (300 if name == "space" else 1000, 50) for name in order})
    font.setupHorizontalHeader(ascent=880, descent=-120)
    # reportlab knows a font by its PostScript name: one per test font.
    family = f"Test{path.stem.title()}"
    font.setupNameTable({"familyName": family, "styleName": "Bold", "psName": f"{family}-Bold"})
    font.setupOS2(sTypoAscender=880, sTypoDescender=-120, usWinAscent=880, usWinDescent=120)
    font.setupPost()
    if variable:
        font.setupFvar([("wght", 400, 400, 700, "Weight")], [])
    font.save(path)
    return path


def test_text_in_other_scripts_is_set_in_the_clients_font(tmp_path):
    font = own_font(tmp_path / "own.ttf", "".join(CHINESE.values()) + "王先生")
    card = cards.make(card_text(texts=CHINESE, name="王先生", font=font, locale="zh"))
    faces = {run.text: run.face for run in runs(card)}
    assert faces["高价收购"] == faces["王先生"] == str(font)
    # Geist still sets what it can: the brand and the phone.
    assert faces["LONE STAR CARS"] == "bold"
    assert faces["(512) 555-0142"] == "bold"
    assert_inside(card)


def test_a_letter_no_font_has_stops_the_card(tmp_path):
    with pytest.raises(cards.CardError, match="CARD_FONT"):
        cards.make(card_text(texts=CHINESE))
    font = own_font(tmp_path / "few.ttf", "高价收购")
    with pytest.raises(cards.CardError, match="Neither the card's font nor CARD_FONT"):
        cards.make(card_text(texts=CHINESE, font=font))


def test_only_a_static_truetype_font_is_taken(tmp_path):
    variable = own_font(tmp_path / "variable.ttf", "".join(CHINESE.values()), variable=True)
    with pytest.raises(cards.CardError, match="variable font"):
        cards.make(card_text(texts=CHINESE, font=variable))
    with pytest.raises(cards.CardError, match="not found"):
        cards.make(card_text(texts=CHINESE, font=tmp_path / "nowhere.ttf"))


def test_scripts_whose_letters_join_are_refused():
    with pytest.raises(cards.CardError, match="Arabic"):
        cards.make(card_text(texts={**texts(), "cta": "احصل على عرض"}))


def test_capitals_follow_the_language():
    turkish = {**texts(), "front_hot": "Nakit", "front_rest": "fiyat"}
    card = cards.make(card_text(texts=turkish, brand_name="Kuzey Oto", locale="tr"))
    printed = {run.text for run in runs(card)}
    assert {"NAKİT", "FİYAT"} <= printed
    assert cards.capitals("fiyat", "en") == "FIYAT"


def test_the_card_prints_the_phone_as_people_there_write_it(tmp_path, monkeypatch):
    env = tmp_path / "acme.env"
    env.write_text(
        f"BRAND_NAME=Acme\nBRAND_PHONE=+1 512-555-0100\nPUBLIC_URL={URL}\n", encoding="utf-8"
    )
    printed = []
    make = cards.make
    monkeypatch.setattr(cards, "make", lambda text: printed.append(text.phone) or make(text))
    card_command(env, None, "", None, None, None, tmp_path / "cards")
    card_command(env, None, "", "512.555.0199", None, None, tmp_path / "cards")
    assert printed == ["(512) 555-0100", "(512) 555-0199"]
