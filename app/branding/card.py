"""A business card for the print shop, with the QR code to the seller form.

    python -m app.cli card --env-file clients/acme.env --name "Mike"

In the size print shops in the client's country know (card_format): US 3.5 x
2 in, Russia 90 x 50 mm, Europe 85 x 55 mm, or any card from 85 x 50 to
92 x 56 mm, such as Japan's 91 x 55 mm. The front is the accent color from edge
to edge, with black or white on it, whichever reads better: the brand, a
headline as large as the card lets it be, what the business takes, and the QR
code on a white plate. The back is dark: a promise and three lines next to
the same code, then the contact person and, largest of all and in the accent,
the phone. The wording is in the locale (card.*); the color, logo, name and
phone come from the client's settings. The headline, the tags, the call to
action and the phone are set in Sofia Sans Extra Condensed, the interface's
display face, the rest in Geist; both draw Latin and Cyrillic letters. Text
in other scripts (Chinese, Korean, Greek...) is set in the client's own font
(CARD_FONT), and a card with a letter neither font has is not made.

The files are made the way print shops ask for them:
- a vector PDF in CMYK with the fonts embedded, the bleed the country's shops
  ask for on every side (0.125 in in the US, 2 mm in Russia, 3 mm in Europe)
  and TrimBox/BleedBox set, plus a copy with crop marks for shops that want
  them;
- no text under 7 pt, and all of it at least 0.2 in inside the trim line;
- flat backgrounds, because gradients band in print: the accent on the
  front, and on the back a rich black that stays well under a 300% total ink
  limit;
- small gray text in black ink only, so a slightly misaligned press cannot
  blur it;
- the QR code in black ink only, on unprinted paper, with the quiet zone and
  the module size rules of app/qr.py;
- black on the accent overprints, as prepress does it, so a press slightly
  out of register leaves no white edge around the letters; a logo, made for
  the dark interface, keeps a dark plate under it there.
A PNG preview shows both sides as they look after trimming.
"""

from __future__ import annotations

import io
import re
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app import qr as qr_codes
from app.branding.assets import WORDMARK_RATIO
from app.branding.colors import RGB, contrast
from app.branding.mark import HOLE, TAG_PATH, outline
from app.services.sources import CARD_SOURCE


@dataclass(frozen=True)
class Format:
    """A card size and its bleed, in points (72 to the inch)."""

    name: str
    trim: tuple[float, float]
    bleed: float
    label: str

    @property
    def page(self) -> tuple[float, float]:
        return self.trim[0] + 2 * self.bleed, self.trim[1] + 2 * self.bleed

    def at(self, x: float, y: float) -> tuple[float, float]:
        """Trim coordinates to page coordinates."""
        return x + self.bleed, y + self.bleed


MM = 72 / 25.4
FORMATS = {
    "3.5x2in": Format(
        "3.5x2in", (252.0, 144.0), 9.0, "3.5 x 2 in, 0.125 in bleed (3.75 x 2.25 in pages)"
    ),
    "90x50mm": Format(
        "90x50mm", (90 * MM, 50 * MM), 2 * MM, "90 x 50 mm, 2 mm bleed (94 x 54 mm pages)"
    ),
    "85x55mm": Format(
        "85x55mm", (85 * MM, 55 * MM), 3 * MM, "85 x 55 mm, 3 mm bleed (91 x 61 mm pages)"
    ),
}
US = FORMATS["3.5x2in"]
# Other metric cards, with the 3 mm bleed most shops ask for. Under 50 mm the
# code and the contact band no longer fit one above the other.
METRIC = re.compile(r"(\d{2}(?:\.\d)?)x(\d{2}(?:\.\d)?)mm")
WIDTHS, HEIGHTS = (85.0, 92.0), (50.0, 56.0)
# Distance of all content from the trim line: the 0.125 in print shops ask
# for, plus room for the cut to wander.
MARGIN = 15.0
MIN_TEXT = 7.0
TOTAL_INK_LIMIT = 3.0
# The QR code's white plate, quiet zone included, and the black rim around it
# on a light accent.
PLATE = 72.0
PLATE_RADIUS = 7.0
RIM = 1.6
# The largest the front's headline and the back's phone are set.
HEADLINE = 50.0
PHONE = 30.0
# Between the letters of the front's tags, and between the tags, in font sizes.
TAG_TRACKING = 0.09
TAG_GAP = 1.5
# Crop marks: outside the bleed, in the extra room around the marked copy.
MARK_ROOM = 24.0
MARK_GAP = 3.0
MARK_LENGTH = 12.0
MARK_WIDTH = 0.25

FONTS = Path(__file__).resolve().parent / "fonts"
# Scripts whose letters join, stack or change order: the PDF is drawn one
# letter at a time and would print them wrong, so such text is refused.
SHAPED = (
    (0x0590, 0x08FF),  # Hebrew, Arabic and the other right-to-left scripts
    (0x0900, 0x0DFF),  # Devanagari to Sinhala
    (0x0E00, 0x0EFF),  # Thai, Lao
    (0x0F00, 0x0FFF),  # Tibetan
    (0x1000, 0x109F),  # Myanmar
    (0x1780, 0x17FF),  # Khmer
    (0xFB1D, 0xFDFF),  # Hebrew and Arabic presentation forms
    (0xFE70, 0xFEFC),
)
FACES = {
    "medium": "Geist-Medium.ttf",
    "semibold": "Geist-SemiBold.ttf",
    "bold": "Geist-Bold.ttf",
    "display": "SofiaSansExtraCondensed-ExtraBold.ttf",
    "display-bold": "SofiaSansExtraCondensed-Bold.ttf",
}
# The height of the capitals, of the font size: Geist, and the display face
# (Sofia Sans Extra Condensed), which sets what is read from a distance.
CAP_HEIGHT = 0.71
DISPLAY_CAP_HEIGHT = 0.655

# The locale's card.* keys.
TEXT_KEYS = (
    "front_hot",
    "front_rest",
    "front_tag_1",
    "front_tag_2",
    "front_tag_3",
    "cta",
    "scan",
    "back_title_1",
    "back_title_2",
    "back_list_1",
    "back_list_2",
    "back_list_3",
)


class CardError(ValueError):
    """The card cannot be made as asked; the message says what to change."""


@dataclass(frozen=True)
class Ink:
    """A printing color, and how it looks on screen for the preview."""

    cmyk: tuple[float, float, float, float]
    rgb: RGB

    @property
    def coverage(self) -> float:
        return sum(self.cmyk)

    def percent(self) -> str:
        return "C{} M{} Y{} K{}".format(*(round(v * 100) for v in self.cmyk))


# Rich black: deep, and well under the total ink limit.
BACKGROUND = Ink((0.70, 0.60, 0.55, 0.70), (30, 32, 35))
CREAM = Ink((0.0, 0.01, 0.04, 0.0), (240, 238, 233))
SOFT = Ink((0.0, 0.0, 0.0, 0.22), (200, 200, 200))
MUTED = Ink((0.0, 0.0, 0.0, 0.45), (150, 150, 150))
PAPER = Ink((0.0, 0.0, 0.0, 0.0), (255, 255, 255))
BLACK = Ink((0.0, 0.0, 0.0, 1.0), (35, 31, 32))
REGISTRATION = Ink((1.0, 1.0, 1.0, 1.0), (0, 0, 0))


def cmyk_for(rgb: RGB) -> tuple[float, float, float, float]:
    """A screen color in CMYK, with black taking the gray component.

    Close for the bright accents this is for; the print shop's proof is the
    final word, and a brand's own CMYK values can be given instead.
    """
    red, green, blue = (channel / 255 for channel in rgb)
    black = 1 - max(red, green, blue)
    if black >= 1:
        return (0.0, 0.0, 0.0, 1.0)
    cyan, magenta, yellow = ((1 - value - black) / (1 - black) for value in (red, green, blue))
    return (round(cyan, 2), round(magenta, 2), round(yellow, 2), round(black, 2))


def accent_ink(rgb: RGB, cmyk: str | None = None) -> Ink:
    return Ink(parse_cmyk(cmyk) if cmyk else cmyk_for(rgb), rgb)


def parse_cmyk(value: str) -> tuple[float, float, float, float]:
    """ "20,0,90,0" in percent, as brand guides and print shops write it."""
    parts = [part.strip().rstrip("%") for part in value.split(",")]
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        numbers = []
    if len(numbers) != 4 or not all(0 <= n <= 100 for n in numbers):
        raise CardError(f"CMYK must be four percentages such as 20,0,90,0, got {value!r}")
    cyan, magenta, yellow, black = (round(n / 100, 3) for n in numbers)
    return (cyan, magenta, yellow, black)


# --- what is drawn ----------------------------------------------------------------------
# Coordinates in points from the top left corner of the page with its bleed.


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    ink: Ink
    radius: float = 0.0
    overprint: bool = False


@dataclass
class Run:
    """A line of text from its left end, at the baseline."""

    x: float
    baseline: float
    text: str
    face: str
    size: float
    ink: Ink
    tracking: float = 0.0  # em
    overprint: bool = False


@dataclass
class Shape:
    points: list[tuple[float, float]]
    ink: Ink
    stroke: float = 0.0  # 0: filled
    overprint: bool = False


@dataclass
class Modules:
    x: float
    y: float
    module: float
    matrix: list[list[bool]]
    ink: Ink


@dataclass
class Picture:
    """A logo, laid onto the flat ink under it so it needs no transparency."""

    x: float
    y: float
    w: float
    h: float
    image: Image.Image  # RGBA
    under: Ink


Op = Box | Run | Shape | Modules | Picture


@dataclass
class CardText:
    """Everything printed on the card besides the locale's wording."""

    brand_name: str
    accent: Ink
    base_url: str
    phone: str = ""
    name: str = ""
    logo: Image.Image | None = None
    texts: dict[str, str] = field(default_factory=dict)
    format: Format = US
    # The client's font for letters Geist lacks (CARD_FONT), and the language
    # for capitals: Turkish "i" capitalizes to "İ".
    font: Path | None = None
    locale: str = "en"


@dataclass
class Card:
    front: list[Op]
    back: list[Op]
    plan: qr_codes.Plan
    accent: Ink
    warnings: list[str]
    format: Format = US


# --- text --------------------------------------------------------------------------------


def card_format(value: str) -> Format:
    """A size by name (FORMATS) or any metric card in range, e.g. 91x55mm."""
    if value in FORMATS:
        return FORMATS[value]
    match = METRIC.fullmatch(value)
    if match:
        width, height = float(match[1]), float(match[2])
        if WIDTHS[0] <= width <= WIDTHS[1] and HEIGHTS[0] <= height <= HEIGHTS[1]:
            pages = f"{width + 6:g} x {height + 6:g} mm pages"
            label = f"{width:g} x {height:g} mm, 3 mm bleed ({pages})"
            return Format(value, (width * MM, height * MM), 3 * MM, label)
    raise CardError(
        f"Card size {value!r}: use 3.5x2in, or millimeters from 85x50mm to 92x56mm such as 90x55mm"
    )


def face_file(face: str) -> Path:
    """One of the card's FACES, or the client's own font, named by its path."""
    return FONTS / FACES[face] if face in FACES else Path(face)


@cache
def pdf_font(face: str) -> str:
    """Registers the face with reportlab once; returns its name there."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    name = f"card-{face}" if face in FACES else f"card-own-{zlib.crc32(face.encode()):08x}"
    pdfmetrics.registerFont(TTFont(name, str(face_file(face))))
    return name


@cache
def letters(face: str) -> frozenset[int]:
    """The characters a face can draw."""
    from reportlab.pdfbase import pdfmetrics

    return frozenset(pdfmetrics.getFont(pdf_font(face)).face.charToGlyph)


def own_font(path: Path) -> str:
    """CARD_FONT, checked: a static TrueType file the PDF can embed."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFError

    if not path.is_file():
        raise CardError(f"CARD_FONT {path} not found")
    advice = "Use a static TrueType .ttf file, e.g. Noto Sans SC Bold from Google Fonts."
    try:
        name = pdf_font(str(path))
    except TTFError as exc:
        raise CardError(f"CARD_FONT {path.name} cannot be embedded ({exc}). {advice}") from None
    if "fvar" in pdfmetrics.getFont(name).face.table:
        raise CardError(f"CARD_FONT {path.name} is a variable font. {advice}")
    return str(path)


# Geist has a few letters the display face lacks (Azerbaijani Ə, Vietnamese Ơ
# and Ư, Kazakh Ұ): a line with one of them is set in Geist, not refused.
PLAIN = {"display": "bold", "display-bold": "bold"}


def needs(line: str) -> set[int]:
    return {ord(char) for char in line if not char.isspace()}


def face_for(text: CardText, line: str, face: str) -> str:
    """The card's face when it has every letter of the line (Geist where the
    display face lacks one), else the client's font."""
    needed = needs(line)
    own = [face, PLAIN[face]] if face in PLAIN else [face]
    for candidate in own:
        if needed <= letters(candidate):
            return candidate
    if text.font is not None and needed <= letters(str(text.font)):
        return str(text.font)
    lacking = needed.difference(*(letters(candidate) for candidate in own))
    if text.font is not None:
        lacking -= letters(str(text.font))
    shown = "".join(chr(code) for code in sorted(lacking)[:12])
    where = (
        f"Neither the card's font nor CARD_FONT ({text.font.name}) has"
        if text.font
        else "The card's font has no"
    )
    raise CardError(
        f"{where} {shown!r} (in {line!r}). Set CARD_FONT to a font for this script, "
        "e.g. Noto Sans SC, JP, KR or Noto Sans from Google Fonts (a static .ttf)."
    )


def faces_for(text: CardText, lines: Sequence[str], face: str) -> list[str]:
    """The same for lines read as one: where one of them takes Geist, the
    others the display face would set follow it, so they stay one piece."""
    faces = [face_for(text, line, face) for line in lines]
    plain = PLAIN.get(face)
    if plain not in faces:
        return faces
    return [
        plain if chosen == face and needs(line) <= letters(plain) else chosen
        for line, chosen in zip(lines, faces, strict=True)
    ]


def rise(line: str, face: str, size: float) -> float:
    """How far the line reaches above its baseline: the capitals of the card's
    fonts, or the client's font measured, where ideographs stand taller."""
    if face in FACES:
        return (DISPLAY_CAP_HEIGHT if face.startswith("display") else CAP_HEIGHT) * size
    top = raster_font(face, 1000).getbbox(line, anchor="ls")[1]
    return max(CAP_HEIGHT, -top / 1000) * size


def shaped(line: str) -> str:
    """The letters of the line in a script the card cannot print, if any."""
    return "".join(char for char in line if any(low <= ord(char) <= high for low, high in SHAPED))


def capitals(line: str, locale: str) -> str:
    """Upper case by the language's rules: Turkish and Azerbaijani "i" is "İ"."""
    if locale.split("-")[0] in ("tr", "az"):
        line = line.replace("i", "İ")
    return line.upper()


def text_width(text: str, face: str, size: float, tracking: float = 0.0) -> float:
    """Width as printed: advance widths plus letter spacing between characters."""
    from reportlab.pdfbase import pdfmetrics

    spacing = tracking * size * max(0, len(text) - 1)
    return pdfmetrics.stringWidth(text, pdf_font(face), size) + spacing


def fit(text: str, face: str, size: float, width: float, what: str, tracking: float = 0.0) -> float:
    """The largest size up to `size` at which the text fits, never under MIN_TEXT."""
    needed = text_width(text, face, size, tracking)
    if needed <= width:
        return size
    fitted = size * width / needed
    if fitted < MIN_TEXT:
        raise CardError(
            f"{what} is too long for the card: {text!r} would print under {MIN_TEXT:g} pt. "
            "Make it shorter."
        )
    return fitted


# --- layout --------------------------------------------------------------------------------


def background(fmt: Format) -> Box:
    # Into the bleed on every side: the cut never shows a white edge.
    return Box(0, 0, *fmt.page, BACKGROUND)


def on_accent_ink(accent: Ink) -> Ink:
    """Black or paper white on the accent, whichever reads better."""
    dark = contrast(accent.rgb, BLACK.rgb)
    light = contrast(accent.rgb, PAPER.rgb)
    return BLACK if dark >= light else PAPER


@dataclass(frozen=True)
class Side:
    """What a side is printed on, and the inks of what stands on it."""

    under: Ink
    ink: Ink  # the brand, headlines, the call to action
    quiet: Ink  # the hint under the code
    overprint: bool  # black prints over the ink under it

    @property
    def dark(self) -> bool:
        return self.under is BACKGROUND


DARK = Side(BACKGROUND, CREAM, MUTED, False)


def accent_side(accent: Ink) -> Side:
    """The front: the accent itself, with black or white on it."""
    ink = on_accent_ink(accent)
    # Black over the accent needs no trapping, while both stay under the limit.
    over = ink is BLACK and accent.coverage + BLACK.coverage <= TOTAL_INK_LIMIT
    return Side(accent, ink, ink, over)


def mark(x: float, y: float, size: float, accent: Ink, side: Side) -> list[Op]:
    """The default mark, the price tag on a rounded square (page coordinates):
    an accent square on the dark side, the other way round on the accent."""
    square, tag = (accent, on_accent_ink(accent)) if side.dark else (side.ink, accent)
    unit = size / 24
    shape = [(x + px * unit, y + py * unit) for px, py in outline(TAG_PATH, steps=6)]
    cx, cy, r = HOLE
    corners = [(1, 0), (0.71, 0.71), (0, 1), (-0.71, 0.71), (-1, 0), (-0.71, -0.71), (0, -1)]
    hole = [
        (x + (cx + r * c) * unit, y + (cy + r * s) * unit) for c, s in [*corners, (0.71, -0.71)]
    ]
    over = side.overprint
    return [
        Box(x, y, size, size, square, radius=size * 7 / 24, overprint=over),
        Shape(shape, tag),
        Shape(hole, square, overprint=over),
    ]


def is_wordmark(logo: Image.Image) -> bool:
    return logo.width >= WORDMARK_RATIO * logo.height


BRAND_HEIGHT = 11.0
# A logo is made for the dark interface: on the accent it keeps a dark plate.
CHIP_PAD = 2.5


def brand_line(
    text: CardText, x: float, y: float, width: float, side: Side
) -> tuple[list[Op], float]:
    """Logo, or the mark and the name, from the top left (trim); and its height."""
    fmt = text.format
    logo = text.logo
    pad = 0.0 if side.dark else CHIP_PAD
    height = BRAND_HEIGHT + 2 * pad
    if logo is not None and is_wordmark(logo):
        scale = min(BRAND_HEIGHT / logo.height, (width - 2 * pad) / logo.width)
        size = (logo.width * scale, logo.height * scale)
        ops: list[Op] = []
        if pad:
            ops.append(Box(*fmt.at(x, y), size[0] + 4 * pad, height, BACKGROUND, radius=3.5))
        left = x + 2 * pad
        ops.append(Picture(*fmt.at(left, y + (height - size[1]) / 2), *size, logo, BACKGROUND))
        return ops, height
    ops = []
    if logo is not None:
        scale = BRAND_HEIGHT / max(logo.width, logo.height)
        if pad:
            ops.append(Box(*fmt.at(x, y), height, height, BACKGROUND, radius=height * 7 / 24))
        ops.append(
            Picture(
                *fmt.at(x + pad, y + pad), logo.width * scale, logo.height * scale, logo, BACKGROUND
            )
        )
    else:
        height = BRAND_HEIGHT
        ops += mark(*fmt.at(x, y), height, text.accent, side)
    name = capitals(text.brand_name, text.locale)
    face = face_for(text, name, "bold")
    size = fit(name, face, 7.5, width - height - 5, "BRAND_NAME", tracking=0.14)
    baseline = y + height / 2 + CAP_HEIGHT * size / 2
    ops.append(
        Run(
            *fmt.at(x + height + 5, baseline),
            name,
            face,
            size,
            side.ink,
            tracking=0.14,
            overprint=side.overprint,
        )
    )
    return ops, height


def arrow(x: float, baseline: float, size: float, height: float, side: Side) -> list[Op]:
    """The arrow the fonts lack: a shaft and a head at mid cap height (page)."""
    middle = baseline - height / 2
    length, head, stroke = 0.6 * size, 0.23 * size, 0.11 * size
    tip = x + length
    over = side.overprint
    return [
        Shape([(x, middle), (tip, middle)], side.ink, stroke=stroke, overprint=over),
        Shape(
            [(tip - head, middle - head), (tip, middle), (tip - head, middle + head)],
            side.ink,
            stroke,
            over,
        ),
    ]


def plate(fmt: Format, left: float, top: float, matrix: list[list[bool]]) -> list[Op]:
    """The QR code on its white plate, `left` and `top` in trim coordinates."""
    modules = len(matrix)
    # The quiet zone of four modules is the plate itself.
    module = PLATE / (modules + 2 * qr_codes.BORDER)
    side = module * modules
    return [
        Box(*fmt.at(left, top), PLATE, PLATE, PAPER, radius=PLATE_RADIUS),
        Modules(
            *fmt.at(left + (PLATE - side) / 2, top + (PLATE - side) / 2), module, matrix, BLACK
        ),
    ]


def qr_column(
    text: CardText, matrix: list[list[bool]], side: Side, top: float | None = None
) -> tuple[list[Op], float, float]:
    """The plate with the code, the call to action and the hint, down the right
    edge: centered, or from `top`. Returns its left edge and its bottom."""
    texts = text.texts
    fmt = text.format
    width, height = fmt.trim
    # On a light accent the white plate gets a black rim, or it would melt
    # into the color; the rim stays inside the margin like everything else.
    rim = RIM if side.ink is BLACK and not side.dark else 0.0
    left = width - MARGIN - PLATE - rim
    cta_gap, hint_gap = 13.5, 9.5
    if top is None:
        top = (height - (PLATE + cta_gap + hint_gap)) / 2 - 2
    top += rim
    ops: list[Op] = []
    if rim:
        ops.append(
            Box(
                *fmt.at(left - rim, top - rim),
                PLATE + 2 * rim,
                PLATE + 2 * rim,
                BLACK,
                radius=PLATE_RADIUS + rim,
                overprint=side.overprint,
            )
        )
    ops += plate(fmt, left, top, matrix)

    cta = capitals(texts["cta"], text.locale)
    face = face_for(text, cta, "display")
    tracking = 0.03
    # Room for the arrow: its length and the gap before it, in font sizes.
    tail = 0.9
    size = 11.5
    needed = text_width(cta, face, size, tracking) + tail * size
    if needed > PLATE:
        size = fit(cta, face, size * PLATE / needed, PLATE, "card.cta", tracking)
    cta_width = text_width(cta, face, size, tracking) + tail * size
    cta_x = left + (PLATE - cta_width) / 2
    baseline = top + PLATE + rim + cta_gap
    ops.append(Run(*fmt.at(cta_x, baseline), cta, face, size, side.ink, tracking, side.overprint))
    ops += arrow(
        *fmt.at(cta_x + cta_width - 0.6 * size, baseline), size, rise(cta, face, size), side
    )

    hint = texts["scan"]
    face = face_for(text, hint, "semibold")
    hint_size = fit(hint, face, MIN_TEXT, PLATE + 6, "card.scan")
    hint_x = left + (PLATE - text_width(hint, face, hint_size)) / 2
    ops.append(
        Run(
            *fmt.at(hint_x, baseline + hint_gap),
            hint,
            face,
            hint_size,
            side.quiet,
            overprint=side.overprint,
        )
    )
    return ops, left - rim, baseline + hint_gap + 0.25 * hint_size


def tag_rows(
    text: CardText, tags: list[str], faces: list[str], width: float
) -> tuple[float, list[float], list[list[int]]]:
    """What the business takes, on one line if it fits at a size worth
    printing, else on several at the smallest: the size, each tag's width and
    which tags stand on which line."""
    sizes = (8.5, 7.75, MIN_TEXT)
    for size in sizes:
        pieces = [
            text_width(tag, face, size, TAG_TRACKING) for tag, face in zip(tags, faces, strict=True)
        ]
        rows: list[list[int]] = [[]]
        used = 0.0
        for index, piece in enumerate(pieces):
            if piece > width:
                break
            if rows[-1] and used + TAG_GAP * size + piece > width:
                rows.append([])
                used = 0.0
            used += (TAG_GAP * size if rows[-1] else 0) + piece
            rows[-1].append(index)
        else:
            if len(rows) == 1 or size == sizes[-1]:
                return size, pieces, rows
            continue
        if size == sizes[-1]:
            raise CardError(
                f"card.front_tag_{index + 1} is too long for the card. Make it shorter."
            )
    raise AssertionError("unreachable")


def front(text: CardText, matrix: list[list[bool]]) -> list[Op]:
    texts = text.texts
    fmt = text.format
    height = fmt.trim[1]
    side = accent_side(text.accent)
    # The accent itself, into the bleed on every side: under a wiper, on a
    # dark windshield, a bright card is the one that gets seen.
    ops: list[Op] = [Box(0, 0, *fmt.page, text.accent)]
    column, column_left, _ = qr_column(text, matrix, side)
    ops += column
    width = column_left - 12 - MARGIN

    # The brand on top, what the business takes at the bottom, and the
    # headline as large as the room between them lets it be.
    brand, brand_height = brand_line(text, MARGIN, MARGIN, width, side)
    ops += brand

    tags = [capitals(texts[f"front_tag_{n}"], text.locale) for n in (1, 2, 3)]
    faces = faces_for(text, tags, "display-bold")
    size, pieces, rows = tag_rows(text, tags, faces, width)
    line = 1.3 * size
    first_tags = height - MARGIN - 1.0 - line * (len(rows) - 1)
    dot = 0.22 * size
    for number, row in enumerate(rows):
        baseline = first_tags + number * line
        x = MARGIN
        for place, index in enumerate(row):
            if place:
                middle = baseline - rise(tags[index], faces[index], size) / 2
                ops.append(
                    Box(
                        *fmt.at(x - (TAG_GAP * size + dot) / 2, middle - dot / 2),
                        dot,
                        dot,
                        side.ink,
                        radius=dot / 2,
                        overprint=side.overprint,
                    )
                )
            ops.append(
                Run(
                    *fmt.at(x, baseline),
                    tags[index],
                    faces[index],
                    size,
                    side.ink,
                    TAG_TRACKING,
                    side.overprint,
                )
            )
            x += pieces[index] + TAG_GAP * size

    hot, rest = (capitals(texts[key], text.locale) for key in ("front_hot", "front_rest"))
    hot_face, rest_face = faces_for(text, (hot, rest), "display")
    headline = min(
        fit(hot, hot_face, HEADLINE, width, "card.front_hot"),
        fit(rest, rest_face, HEADLINE, width, "card.front_rest"),
    )
    above = MARGIN + brand_height + 5
    below = first_tags - max(rise(tag, face, size) for tag, face in zip(tags, faces, strict=True))
    below -= 5

    def block(at: float) -> tuple[float, float]:
        # The display face's capitals sit 0.835 apart; taller letters get the same gap.
        top = rise(hot, hot_face, at)
        return top, max(0.835 * at, rise(rest, rest_face, at) + 0.18 * at)

    top, leading = block(headline)
    if top + leading > below - above:
        headline *= (below - above) / (top + leading)
        top, leading = block(headline)
    # The narrow display face needs more height to stand out than a face of
    # ordinary width (Geist, or the client's own font).
    least = 24.0 if {hot_face, rest_face} <= PLAIN.keys() else 16.0
    if headline < least:
        raise CardError(
            "The headline is too long to stand out on the card. "
            "Make card.front_hot and card.front_rest shorter."
        )
    first = above + (below - above - top - leading) / 2 + top
    for line_text, face, baseline in ((hot, hot_face, first), (rest, rest_face, first + leading)):
        ops.append(
            Run(
                *fmt.at(MARGIN, baseline),
                line_text,
                face,
                headline,
                side.ink,
                overprint=side.overprint,
            )
        )
    return ops


def back(text: CardText, matrix: list[list[bool]]) -> list[Op]:
    texts = text.texts
    fmt = text.format
    width, height = fmt.trim
    ops: list[Op] = [background(fmt)]

    # The code again, as large as on the front: a card is often picked up
    # back side first. In the top right corner, so the phone has the bottom.
    column, column_left, column_bottom = qr_column(text, matrix, DARK, top=MARGIN)
    ops += column
    room = column_left - 12 - MARGIN

    # The promise and what the business takes, left of the code.
    titles = [capitals(texts[f"back_title_{n}"], text.locale) for n in (1, 2)]
    title_faces = faces_for(text, titles, "display")
    size = min(
        fit(title, face, 19.5, room, f"card.back_title_{n}")
        for n, (title, face) in enumerate(zip(titles, title_faces, strict=True), 1)
    )
    baseline = MARGIN + rise(titles[0], title_faces[0], size)
    ops.append(Run(*fmt.at(MARGIN, baseline), titles[0], title_faces[0], size, CREAM))
    baseline += max(0.9 * size, rise(titles[1], title_faces[1], size) + 0.24 * size)
    ops.append(Run(*fmt.at(MARGIN, baseline), titles[1], title_faces[1], size, CREAM))
    baseline += 14
    square = 3.2
    for n in (1, 2, 3):
        item = texts[f"back_list_{n}"]
        face = face_for(text, item, "medium")
        item_size = fit(item, face, 8.0, room - 9, f"card.back_list_{n}")
        middle = baseline - CAP_HEIGHT * item_size / 2
        ops.append(
            Box(*fmt.at(MARGIN, middle - square / 2), square, square, text.accent, radius=0.9)
        )
        ops.append(Run(*fmt.at(MARGIN + 9, baseline), item, face, item_size, SOFT))
        baseline += 11.5
    list_bottom = baseline - 11.5 + 0.25 * 8.0

    # The contact along the bottom: the person's name if given, and the phone
    # as the largest thing on this side, in the accent. The address is in the
    # code.
    name_size, name_gap = 8.0, 6.0
    # Room under the baseline for what hangs below it at the phone's size.
    bottom = height - max(MARGIN, 9 + 0.25 * PHONE if text.phone else 0)
    if text.phone:
        face = face_for(text, text.phone, "display")
        # No taller than the room under the list (and the name) allows.
        taken = name_gap + CAP_HEIGHT * name_size if text.name else 0.0
        tallest = (bottom - list_bottom - 4 - taken) / (rise(text.phone, face, 1000) / 1000)
        phone_size = min(PHONE, tallest)
        # Beside the code's column, unless it stands clear below it.
        clear = bottom - rise(text.phone, face, phone_size) >= column_bottom + 3
        limit = width - 2 * MARGIN if clear else room
        phone_size = fit(text.phone, face, phone_size, limit, "The phone")
        ops.append(Run(*fmt.at(MARGIN, bottom), text.phone, face, phone_size, text.accent))
        bottom -= rise(text.phone, face, phone_size) + name_gap
    if text.name:
        face = face_for(text, text.name, "semibold")
        name_size = fit(text.name, face, name_size, room, "The name (--name)")
        ops.append(Run(*fmt.at(MARGIN, bottom), text.name, face, name_size, SOFT))
    return ops


def make(text: CardText) -> Card:
    """Both sides laid out and checked, or a CardError saying what to change."""
    missing = [key for key in TEXT_KEYS if not text.texts.get(key)]
    if missing:
        raise CardError("Missing card texts in the locale: " + ", ".join(missing))
    if text.accent.coverage > TOTAL_INK_LIMIT:
        raise CardError(f"The accent's CMYK ({text.accent.percent()}) is over the 300% ink limit.")
    for line in (text.brand_name, text.name, text.phone, *text.texts.values()):
        if shaped(line):
            raise CardError(
                f"{line!r} is in a script whose letters join or change shape (such as Arabic, "
                "Hebrew, Hindi or Thai), which the card cannot print yet. Write the card's "
                "texts in a script it can print, or have a print shop set this text."
            )
    if text.font is not None:
        own_font(text.font)
    url = qr_codes.link(text.base_url, CARD_SOURCE)
    matrix = [[bool(cell) for cell in row] for row in qr_codes.code(url).matrix]
    modules = len(matrix)
    symbol_mm = PLATE / 72 * 25.4 * modules / (modules + 2 * qr_codes.BORDER)
    checked = qr_codes.plan(text.base_url, CARD_SOURCE, size_mm=symbol_mm)
    if checked.problems:
        raise CardError("; ".join(checked.problems))
    warnings = list(checked.warnings)
    if contrast(text.accent.rgb, BACKGROUND.rgb) < 4.5:
        warnings.append(
            "The accent reads weakly on the card's dark side, where it sets the phone; "
            "a lighter shade prints better."
        )
    return Card(
        front(text, matrix), back(text, matrix), checked, text.accent, warnings, text.format
    )


# --- PDF ---------------------------------------------------------------------------------


def logo_in_cmyk(image: Image.Image, under: Ink) -> Image.Image:
    """The logo laid onto a flat ink, in CMYK: nothing transparent to flatten."""
    rgb = image.convert("RGB").tobytes()
    alpha = image.getchannel("A").tobytes()
    out = bytearray()
    for index, opacity in enumerate(alpha):
        pixel = (rgb[index * 3], rgb[index * 3 + 1], rgb[index * 3 + 2])
        share = opacity / 255
        own = cmyk_for(pixel)
        out += bytes(
            round(255 * (share * mine + (1 - share) * base))
            for mine, base in zip(own, under.cmyk, strict=True)
        )
    return Image.frombytes("CMYK", image.size, bytes(out))


def draw_pdf(canvas: Any, ops: Sequence[Op], offset: float, fmt: Format) -> None:
    from reportlab.lib.colors import CMYKColor
    from reportlab.lib.utils import ImageReader

    page_height = fmt.page[1] + 2 * offset

    def color(ink: Ink) -> CMYKColor:
        return CMYKColor(*ink.cmyk)

    def x(value: float) -> float:
        return value + offset

    def y(value: float) -> float:
        # PDF counts from the bottom.
        return page_height - offset - value

    def overprint(on: bool) -> None:
        # With the mode that leaves alone the inks a color has none of: black
        # then prints over the accent instead of cutting a hole in it.
        canvas.setFillOverprint(on)
        canvas.setStrokeOverprint(on)
        canvas.setOverprintMask(on)

    for op in ops:
        overprint(getattr(op, "overprint", False))
        if isinstance(op, Box):
            canvas.setFillColor(color(op.ink))
            if op.radius:
                canvas.roundRect(x(op.x), y(op.y + op.h), op.w, op.h, op.radius, stroke=0, fill=1)
            else:
                canvas.rect(x(op.x), y(op.y + op.h), op.w, op.h, stroke=0, fill=1)
        elif isinstance(op, Run):
            canvas.setFillColor(color(op.ink))
            line = canvas.beginText(x(op.x), y(op.baseline))
            line.setFont(pdf_font(op.face), op.size)
            line.setCharSpace(op.tracking * op.size)
            line.textOut(op.text)
            canvas.drawText(line)
        elif isinstance(op, Shape):
            path = canvas.beginPath()
            (first_x, first_y), *rest = op.points
            path.moveTo(x(first_x), y(first_y))
            for point_x, point_y in rest:
                path.lineTo(x(point_x), y(point_y))
            if op.stroke:
                canvas.setStrokeColor(color(op.ink))
                canvas.setLineWidth(op.stroke)
                canvas.setLineCap(1)
                canvas.setLineJoin(1)
                canvas.drawPath(path, stroke=1, fill=0)
            else:
                path.close()
                canvas.setFillColor(color(op.ink))
                canvas.drawPath(path, stroke=0, fill=1)
        elif isinstance(op, Modules):
            # One path of runs of dark modules: no seams between neighbours.
            canvas.setFillColor(color(op.ink))
            path = canvas.beginPath()
            for row, cells in enumerate(op.matrix):
                column = 0
                while column < len(cells):
                    if not cells[column]:
                        column += 1
                        continue
                    start = column
                    while column < len(cells) and cells[column]:
                        column += 1
                    path.rect(
                        x(op.x + start * op.module),
                        y(op.y + (row + 1) * op.module),
                        (column - start) * op.module,
                        op.module,
                    )
            canvas.drawPath(path, stroke=0, fill=1)
        elif isinstance(op, Picture):
            image = ImageReader(logo_in_cmyk(op.image, op.under))
            canvas.drawImage(image, x(op.x), y(op.y + op.h), op.w, op.h)
    overprint(False)


def crop_marks(canvas: Any, offset: float, fmt: Format) -> None:
    """Short lines on the trim lines, starting just outside the bleed."""
    from reportlab.lib.colors import CMYKColor

    canvas.setStrokeColor(CMYKColor(*REGISTRATION.cmyk))
    canvas.setLineWidth(MARK_WIDTH)
    page_width, page_height = fmt.page[0] + 2 * offset, fmt.page[1] + 2 * offset
    low = offset - MARK_GAP
    high_x, high_y = page_width - low, page_height - low
    for trim_x in (offset + fmt.bleed, offset + fmt.bleed + fmt.trim[0]):
        canvas.line(trim_x, low, trim_x, low - MARK_LENGTH)
        canvas.line(trim_x, high_y, trim_x, high_y + MARK_LENGTH)
    for trim_y in (offset + fmt.bleed, offset + fmt.bleed + fmt.trim[1]):
        canvas.line(low, trim_y, low - MARK_LENGTH, trim_y)
        canvas.line(high_x, trim_y, high_x + MARK_LENGTH, trim_y)


def write_pdf(card: Card, path: Path, title: str, marks: bool) -> None:
    from reportlab.pdfgen.canvas import Canvas

    fmt = card.format
    offset = MARK_ROOM if marks else 0.0
    size = (fmt.page[0] + 2 * offset, fmt.page[1] + 2 * offset)
    # enforceColorSpace: reportlab refuses any color that is not CMYK.
    canvas = Canvas(str(path), pagesize=size, pageCompression=1, enforceColorSpace="cmyk")
    canvas.setTitle(title)
    canvas.setSubject(f"Business card {fmt.label}, CMYK")
    canvas.setCreator("cash-for-cars-lead-system")
    for ops in (card.front, card.back):
        canvas.setBleedBox((offset, offset, offset + fmt.page[0], offset + fmt.page[1]))
        trim_left = offset + fmt.bleed
        canvas.setTrimBox((trim_left, trim_left, trim_left + fmt.trim[0], trim_left + fmt.trim[1]))
        draw_pdf(canvas, ops, offset, fmt)
        if marks:
            crop_marks(canvas, offset, fmt)
        canvas.showPage()
    canvas.save()


# --- preview -------------------------------------------------------------------------------


@cache
def raster_font(face: str, pixels: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(face_file(face), pixels)


def render(ops: Sequence[Op], fmt: Format = US, dpi: int = 300) -> Image.Image:
    """One side on screen, from the same drawing as the PDF, trimmed."""
    scale = dpi / 72
    image = Image.new("RGB", (round(fmt.page[0] * scale), round(fmt.page[1] * scale)), PAPER.rgb)
    draw = ImageDraw.Draw(image)

    def p(value: float) -> float:
        return value * scale

    for op in ops:
        if isinstance(op, Box):
            box = (p(op.x), p(op.y), p(op.x + op.w), p(op.y + op.h))
            draw.rounded_rectangle(box, radius=p(op.radius), fill=op.ink.rgb)
        elif isinstance(op, Run):
            # Character by character with the PDF's widths, so both agree.
            font = raster_font(op.face, max(1, round(p(op.size))))
            left = op.x
            for char in op.text:
                draw.text((p(left), p(op.baseline)), char, font=font, fill=op.ink.rgb, anchor="ls")
                left += text_width(char, op.face, op.size) + op.tracking * op.size
        elif isinstance(op, Shape):
            points = [(p(px), p(py)) for px, py in op.points]
            if op.stroke:
                stroke = max(1, round(p(op.stroke)))
                draw.line(points, fill=op.ink.rgb, width=stroke, joint="curve")
                for cx, cy in (points[0], points[-1]):
                    r = stroke / 2
                    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=op.ink.rgb)
            else:
                draw.polygon(points, fill=op.ink.rgb)
        elif isinstance(op, Modules):
            for row, cells in enumerate(op.matrix):
                for column, dark in enumerate(cells):
                    if dark:
                        left, top = p(op.x + column * op.module), p(op.y + row * op.module)
                        right, bottom = left + p(op.module), top + p(op.module)
                        draw.rectangle((left, top, right, bottom), fill=op.ink.rgb)
        elif isinstance(op, Picture):
            size = (max(1, round(p(op.w))), max(1, round(p(op.h))))
            logo = op.image.resize(size, Image.Resampling.LANCZOS)
            image.paste(logo.convert("RGB"), (round(p(op.x)), round(p(op.y))), logo)
    left = top = round(p(fmt.bleed))
    return image.crop((left, top, left + round(p(fmt.trim[0])), top + round(p(fmt.trim[1]))))


def preview(card: Card) -> Image.Image:
    """Both sides as they look after trimming, for a quick look in a chat."""
    width, gap = 900, 40
    sides = []
    for ops in (card.front, card.back):
        side = render(ops, card.format)
        height = round(width * side.height / side.width)
        sides.append(side.resize((width, height), Image.Resampling.LANCZOS))
    sheet = Image.new("RGB", (width + 2 * gap, 2 * sides[0].height + 3 * gap), (214, 211, 205))
    for index, side in enumerate(sides):
        sheet.paste(side, (gap, gap + index * (side.height + gap)))
    return sheet


def save(card: Card, out_dir: Path, stem: str, title: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "pdf": out_dir / f"{stem}.pdf",
        "marks": out_dir / f"{stem}-crop-marks.pdf",
        "preview": out_dir / f"{stem}-preview.png",
    }
    write_pdf(card, paths["pdf"], title, marks=False)
    write_pdf(card, paths["marks"], title, marks=True)
    preview(card).save(paths["preview"], optimize=True)
    return paths


def logo_image(body: bytes) -> Image.Image:
    return Image.open(io.BytesIO(body)).convert("RGBA")
