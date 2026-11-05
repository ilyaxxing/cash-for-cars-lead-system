"""Build the site installers send car buyers to, into a folder.

    .venv/bin/python tools/make_buyer_site.py OUT

The page for car buyers (buyer-site/index.html, a template) is filled in
for every country in countries/ from its demo.yaml: the United States at
the root, every other country at /<code>/. The live demo (docs/demo) and
the fonts and card pictures the pages show go with them, and each country's
link preview picture: its headline and its sample card. It is published
apart from the project page, on a site of its own (a GitHub organization's
<name>.github.io): a buyer who shortens the address must not land on the
installers' page with its prices. Run tools/make_demo.py first when the
form, the dashboard or a country changed; this only gathers what is built.

OUT may be a clone of the site's repository: everything in it except .git is
replaced, then commit and push there (docs/README.md).
"""

from __future__ import annotations

import hashlib
import html
import io
import re
import shutil
import sys
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.make_demo import CARDS, DEFAULT, country_codes, load_demo  # noqa: E402

DOCS = ROOT / "docs"
TEMPLATE = ROOT / "buyer-site" / "index.html"
TOKEN = re.compile(r"\{\{(\w+)\}\}")
NOTE = re.compile(r"<!-- A template:.*?-->\n")
# Shared with the project page: the fonts and the sample card in six colors.
ASSETS = ("fonts", "card")
# The headline may mark its accented words with <em>; every other text is plain.
MARKUP = {"h1"}

# Where the site is published (docs/README.md): a link preview needs the
# picture's full address.
SITE = "https://car-buyer-demo.github.io/"
# The picture a messenger shows under a link to the page, in the page's colors.
PREVIEW_SIZE = (1200, 630)
FONTS = ROOT / "app" / "branding" / "fonts"
BACKGROUND = (11, 12, 12)
TEXT = (244, 243, 238)
MUTED = (165, 167, 162)
ACCENT = (199, 247, 71)
# Search engines stay out. The apps that show a link's preview read the page
# for it, and some of them heed robots.txt too: they may.
PREVIEWERS = (
    "TelegramBot",
    "WhatsApp",
    "facebookexternalhit",
    "Facebot",
    "Twitterbot",
    "Slackbot-LinkExpanding",
    "Discordbot",
    "LinkedInBot",
    "vkShare",
)
ROBOTS = (
    "User-agent: *\nDisallow: /\n\n"
    + "".join(f"User-agent: {name}\n" for name in PREVIEWERS)
    + "Allow: /\n"
)


def plain(text: str) -> str:
    """Text for the page, in an element or a double-quoted attribute."""
    return html.escape(text, quote=False).replace('"', "&quot;")


def headline_lines(
    h1: str, font: ImageFont.FreeTypeFont, width: float
) -> list[list[tuple[str, tuple]]]:
    """The headline as lines of (word, color) that fit the width; its accented
    part starts a line of its own, as on a wide page."""
    lines = []
    for index, part in enumerate(re.split(r"</?em>", h1)):
        color = ACCENT if index % 2 else TEXT
        line: list[tuple[str, tuple]] = []
        used = 0.0
        for word in part.split():
            gap = font.getlength(" ") if line else 0.0
            if line and used + gap + font.getlength(word) > width:
                lines.append(line)
                line, used, gap = [], 0.0, 0.0
            line.append((word, color))
            used += gap + font.getlength(word)
        if line:
            lines.append(line)
    return lines


def tilted_card(path: Path, width: int, angle: float) -> Image.Image:
    """A sample card with round corners, turned as on the page."""
    card = Image.open(path).convert("RGB")
    card = card.resize((width, round(card.height * width / card.width)), Image.Resampling.LANCZOS)
    corners = Image.new("L", card.size, 0)
    ImageDraw.Draw(corners).rounded_rectangle(
        (0, 0, card.width - 1, card.height - 1), radius=round(width * 0.025), fill=255
    )
    card.putalpha(corners)
    return card.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def lay(canvas: Image.Image, card: Image.Image, center: tuple[float, float]) -> None:
    """A card centered on a point, over a soft shadow."""
    x, y = round(center[0] - card.width / 2), round(center[1] - card.height / 2)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 255), (x, y + 24), card.getchannel("A").point(lambda a: a * 0.6))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))
    canvas.alpha_composite(card, (x, y))


@cache
def preview(code: str) -> bytes:
    """The link preview picture for one country: its headline and its sample card."""
    texts = load_demo(code)["page"]
    cards = CARDS / code if code != DEFAULT else CARDS
    return poster(cards, texts["kicker_hero"], texts["h1"])


def poster(cards: Path, kicker: str, h1: str, size: tuple[int, int] = PREVIEW_SIZE) -> bytes:
    """A link preview picture: a kicker and a headline beside a sample card."""
    canvas = Image.new("RGBA", size, (*BACKGROUND, 255))
    width, height = size

    # The front and back of the card on the right, laid out as on the page.
    left, room = 612, width - 612 - 40
    tall = room * 3.1 / 3.5
    top = (height - tall) / 2
    card_w = round(room * 0.72)
    with Image.open(cards / "lime-front.webp") as sample:
        card_h = card_w * sample.height / sample.width
    front = tilted_card(cards / "lime-front.webp", card_w, 4)
    back = tilted_card(cards / "lime-back.webp", card_w, -3)
    lay(canvas, back, (left + room - card_w / 2, top + tall - card_h / 2))
    lay(canvas, front, (left + card_w / 2, top + card_h / 2))

    # The kicker and the headline on the left, at one size in every language
    # unless a long one needs less.
    text_width, text_height = 520, 360
    bold = FONTS / "Geist-ExtraBold.ttf"
    for size in range(68, 40, -2):
        font = ImageFont.truetype(str(bold), size)
        lines = headline_lines(h1, font, text_width)
        if len(lines) * size * 0.98 <= text_height and all(
            font.getlength(" ".join(word for word, _ in line)) <= text_width for line in lines
        ):
            break
    kicker = kicker.upper()
    for small in range(20, 12, -1):
        mono = ImageFont.truetype(str(FONTS / "GeistMono-Medium.ttf"), small)
        if 21 + sum(mono.getlength(letter) + small * 0.12 for letter in kicker) <= text_width:
            break
    block = 20 + 34 + len(lines) * size * 0.98
    y = (height - block) / 2
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((72, y + 5, 81, y + 14), radius=2, fill=ACCENT)
    x = 72 + 9 + 12
    for letter in kicker:
        draw.text((x, y + 17), letter, font=mono, fill=MUTED, anchor="ls")
        x += mono.getlength(letter) + small * 0.12
    y += 20 + 34
    for line in lines:
        x = 72
        for word, color in line:
            draw.text((x, y + size * 0.8), word, font=font, fill=color, anchor="ls")
            x += font.getlength(word + " ")
        y += size * 0.98

    out = io.BytesIO()
    canvas.convert("RGB").save(out, "JPEG", quality=85, optimize=True, progressive=True)
    return out.getvalue()


def page(code: str) -> str:
    """The page for car buyers in one country's language."""
    demo = load_demo(code)
    # A named link puts the business's name in the title in place of the brand.
    if demo["business"]["brand_name"] not in demo["page"]["title"]:
        raise SystemExit(f"countries/{code}/demo.yaml: page title must hold the brand_name")
    texts = {key: value if key in MARKUP else plain(value) for key, value in demo["page"].items()}
    deeper = code != DEFAULT
    cards = CARDS / code if deeper else CARDS
    width, height = Image.open(cards / "lime-front.webp").size
    # The picture's address changes with it, so a messenger fetches it anew.
    version = hashlib.sha256(preview(code)).hexdigest()[:10]
    values = {
        **texts,
        "preview_title": plain(re.sub(r"</?em>", "", demo["page"]["h1"])),
        "preview_image": f"{SITE}assets/preview/{code}.jpg?v={version}",
        "lang": demo["lang"],
        "brand_name": plain(demo["business"]["brand_name"]),
        "root": "../" if deeper else "./",
        "demo": f"../demo/{code}/" if deeper else "demo/",
        "cards": f"{code}/" if deeper else "",
        "card_width": str(width),
        "card_height": str(height),
    }
    # The note on the template itself is for this repository, not for buyers.
    template = NOTE.sub("", TEMPLATE.read_text(encoding="utf-8"), count=1)
    used = set(TOKEN.findall(template))
    if used - values.keys() or texts.keys() - used:
        missing = ", ".join(sorted(used - values.keys())) or "none"
        unused = ", ".join(sorted(texts.keys() - used)) or "none"
        raise SystemExit(f"countries/{code}/demo.yaml page: missing {missing}; unused {unused}")
    return TOKEN.sub(lambda match: values[match[1]], template)


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for entry in out.iterdir():
        if entry.name == ".git":
            continue
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    for code in country_codes():
        folder = out if code == DEFAULT else out / code
        folder.mkdir(exist_ok=True)
        (folder / "index.html").write_text(page(code), encoding="utf-8")
    shutil.copytree(DOCS / "demo", out / "demo")
    for name in ASSETS:
        shutil.copytree(DOCS / "assets" / name, out / "assets" / name)
    (out / "assets" / "preview").mkdir()
    for code in country_codes():
        (out / "assets" / "preview" / f"{code}.jpg").write_bytes(preview(code))
    # Served as it is, never listed by search engines, and a lost address
    # (the dashboard's /app/leads/<id> after a reload) leads back to the page.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (out / "404.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
        '<meta http-equiv="refresh" content="0; url=/"><title>Demo</title>'
        '<a href="/">Open the demo</a>\n',
        encoding="utf-8",
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit("OUT must be a folder outside this repository")
    build(out)
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file() and ".git" not in f.parts)
    print(f"buyer site: {out} ({size // 1024} KB)")


if __name__ == "__main__":
    main()
