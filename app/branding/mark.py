"""The default logo mark, drawn with Pillow: a price tag on an accent square.

frontend/src/shared/TagGlyph.svelte draws the same shape in the interface;
this copy draws it into the home-screen icons and the notification badge
when the client has no icon of their own.
"""

from __future__ import annotations

import re

from PIL import Image, ImageDraw, ImageFont

# The tag outline in the mark's 24x24 box, as in TagGlyph.svelte.
TAG_PATH = (
    "M5 6.8v4.6c0 .5.2 1 .6 1.4l6.1 6.1c.8.8 2 .8 2.8 0l4.1-4.1c.8-.8.8-2 0-2.8"
    "l-6.1-6.1c-.4-.4-.9-.6-1.4-.6H6.8C5.8 5.3 5 6 5 6.8z"
)
HOLE = (8.4, 8.6, 1.3)
DOLLAR_AT = (13.6, 13.0)
# Drawn this many times larger, then scaled down for smooth edges.
SUPERSAMPLE = 4

Color = tuple[int, ...]


def outline(path: str, steps: int = 12) -> list[tuple[float, float]]:
    """Points along an SVG path using M, H, v, l, c and C (what TAG_PATH needs)."""
    tokens = re.findall(r"[A-Za-z]|-?\d*\.?\d+", path)
    points: list[tuple[float, float]] = []
    x = y = 0.0
    command = ""
    i = 0

    def number() -> float:
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    while i < len(tokens):
        if re.fullmatch(r"[A-Za-z]", tokens[i]):
            command = tokens[i]
            i += 1
            if command in "zZ":
                continue
        if command == "M":
            x, y = number(), number()
            points.append((x, y))
        elif command == "H":
            x = number()
            points.append((x, y))
        elif command == "v":
            y += number()
            points.append((x, y))
        elif command == "l":
            x, y = x + number(), y + number()
            points.append((x, y))
        elif command in "cC":
            values = [number() for _ in range(6)]
            if command == "c":
                values = [v + (x if k % 2 == 0 else y) for k, v in enumerate(values)]
            x1, y1, x2, y2, x3, y3 = values
            for step in range(1, steps + 1):
                t = step / steps
                u = 1 - t
                points.append(
                    (
                        u**3 * x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
                        u**3 * y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3,
                    )
                )
            x, y = x3, y3
    return points


def draw_tag(
    image: Image.Image,
    left: float,
    top: float,
    size: float,
    ink: Color,
    paper: Color,
    dollar: bool,
) -> None:
    """The tag (ink) with its hole and $ cut in paper, in a size x size box."""
    unit = size / 24
    draw = ImageDraw.Draw(image)
    draw.polygon([(left + px * unit, top + py * unit) for px, py in outline(TAG_PATH)], fill=ink)
    cx, cy, r = HOLE
    draw.ellipse(
        (
            left + (cx - r) * unit,
            top + (cy - r) * unit,
            left + (cx + r) * unit,
            top + (cy + r) * unit,
        ),
        fill=paper,
    )
    if not dollar:
        return
    # The $ is drawn upright on its own layer, then turned with the tag.
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    font = ImageFont.load_default(size=7.5 * unit)
    center = (left + DOLLAR_AT[0] * unit, top + DOLLAR_AT[1] * unit)
    ImageDraw.Draw(layer).text(
        center,
        "$",
        font=font,
        fill=paper,
        anchor="mm",
        stroke_width=round(0.35 * unit),
        stroke_fill=paper,
    )
    image.alpha_composite(layer.rotate(45, center=center, resample=Image.Resampling.BICUBIC))


def mark_icon(
    size: int, mark_share: float, background: Color, accent: Color, on_accent: Color
) -> Image.Image:
    """The mark centered on a square background; mark_share is its share of the width."""
    big = size * SUPERSAMPLE
    image = Image.new("RGBA", (big, big), (*background[:3], 255))
    mark = big * mark_share
    left = (big - mark) / 2
    ImageDraw.Draw(image).rounded_rectangle(
        (left, left, left + mark, left + mark), radius=mark * 7 / 24, fill=(*accent[:3], 255)
    )
    draw_tag(image, left, left, mark, (*on_accent[:3], 255), (*accent[:3], 255), dollar=True)
    return image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)


def badge(size: int) -> Image.Image:
    """Monochrome badge for the Android status bar: a white tag on transparency.

    Android draws it in one color of its own, so it is the same for every client.
    """
    big = size * SUPERSAMPLE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    # The tag alone fills the badge.
    mark = big * 1.25
    offset = (big - mark) / 2
    draw_tag(image, offset, offset, mark, (255, 255, 255, 255), (0, 0, 0, 0), dollar=False)
    return image.resize((size, size), Image.Resampling.LANCZOS)
