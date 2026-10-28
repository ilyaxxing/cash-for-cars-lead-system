"""The accent color (BRAND_COLOR) and everything derived from it.

One color drives the client's look: buttons, links, selected answers, the
default logo mark and the home-screen icon. The rest of the palette is the
designs' dark theme and stays as it is, so the one thing to check is that
the color can be read on it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

RGB = tuple[int, int, int]

# The designs' lime.
DEFAULT_COLOR = "#C7F747"
# The form's background (--bg); the dashboard's is darker still.
BACKGROUND: RGB = (17, 18, 18)
# Text on a light accent (the designs' near-black) or on a dark one.
DARK: RGB = (17, 18, 18)
LIGHT: RGB = (255, 255, 255)
# WCAG's minimum for large text and interface parts: the accent fills
# buttons and draws outlines and large numbers, and links are underlined.
MIN_CONTRAST = 3.0
# What a suggested replacement aims for: comfortably readable.
GOOD_CONTRAST = 4.5

HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})")


def parse(value: str) -> RGB:
    match = HEX_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"{value!r} is not a color such as #C7F747")
    number = int(match.group(1), 16)
    return (number >> 16) & 255, (number >> 8) & 255, number & 255


def to_hex(rgb: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def luminance(rgb: RGB) -> float:
    """Relative luminance as WCAG defines it."""

    def linear(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: RGB, second: RGB) -> float:
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def mix(color: RGB, other: RGB, share: float) -> RGB:
    """color with `share` of other mixed in."""
    return tuple(round(a + (b - a) * share) for a, b in zip(color, other, strict=True))  # type: ignore[return-value]


def lighter(rgb: RGB, target: float = GOOD_CONTRAST) -> RGB:
    """The same color mixed with white until it reads on the dark background."""
    for step in range(1, 21):
        candidate = mix(rgb, LIGHT, step / 20)
        if contrast(candidate, BACKGROUND) >= target:
            return candidate
    return LIGHT


def check_color(value: str) -> str:
    """BRAND_COLOR as #RRGGBB in capitals, or an error that says what to use."""
    try:
        rgb = parse(value)
    except ValueError:
        raise ValueError(f"BRAND_COLOR must be a color such as #C7F747, got {value!r}") from None
    if contrast(rgb, BACKGROUND) < MIN_CONTRAST:
        raise ValueError(
            f"BRAND_COLOR {to_hex(rgb)} is too dark to read on the app's dark screens. "
            f"A lighter shade of the same color works, for example {to_hex(lighter(rgb))}"
        )
    return to_hex(rgb)


@dataclass(frozen=True)
class Palette:
    """The accent and the colors that go with it, for CSS and the icons."""

    accent: RGB

    @classmethod
    def from_hex(cls, value: str) -> Palette:
        return cls(parse(value))

    @property
    def on_accent(self) -> RGB:
        """Text and icons on the accent: whichever of dark or white reads better."""
        dark, light = contrast(self.accent, DARK), contrast(self.accent, LIGHT)
        return DARK if dark >= light else LIGHT

    @property
    def hover(self) -> RGB:
        return mix(self.accent, LIGHT, 0.2)

    @property
    def pressed(self) -> RGB:
        # Busy and disabled buttons: a touch darker than the accent.
        return mix(self.accent, (0, 0, 0), 0.09)

    def css_variables(self) -> dict[str, str]:
        def channels(rgb: RGB) -> str:
            return " ".join(str(channel) for channel in rgb)

        return {
            "--accent": to_hex(self.accent),
            "--accent-rgb": channels(self.accent),
            "--accent-hover": to_hex(self.hover),
            "--accent-pressed": to_hex(self.pressed),
            "--on-accent": to_hex(self.on_accent),
            "--on-accent-rgb": channels(self.on_accent),
        }

    def style(self) -> str:
        """A <style> element that overrides the defaults in shared/base.css.

        The bundle's stylesheet is linked after it in the page, so the
        selector is doubled to win on specificity rather than on order.
        """
        rules = ";".join(f"{name}:{value}" for name, value in self.css_variables().items())
        return f'<style id="brand-colors">:root:root{{{rules}}}</style>'
