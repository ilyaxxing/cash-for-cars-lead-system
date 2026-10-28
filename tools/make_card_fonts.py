"""Build the business card's fonts from the frontend's Geist packages.

    .venv/bin/python tools/make_card_fonts.py

The card PDF embeds TrueType, and the @fontsource packages ship WOFF files cut
into subsets (Latin, Latin Extended, Cyrillic). For each weight the card uses,
this merges the subsets into one TrueType font in app/branding/fonts/, so a
card prints in English, in Czech or Polish names, and in Russian. Needs
`npm install` in frontend/ first, and fontTools (requirements-dev.txt).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fontTools.merge import Merger
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "frontend" / "node_modules" / "@fontsource"
OUT = ROOT / "app" / "branding" / "fonts"

# The file each weight is saved as, and where it comes from.
FONTS = {
    "Geist-Medium": ("geist", 500),
    "Geist-SemiBold": ("geist", 600),
    "Geist-Bold": ("geist", 700),
    "Geist-ExtraBold": ("geist", 800),
    "GeistMono-Medium": ("geist-mono", 500),
}
SUBSETS = ("latin", "latin-ext", "cyrillic")


def build(name: str, family: str, weight: int, work: Path) -> Path:
    parts = []
    for subset in SUBSETS:
        source = PACKAGES / family / "files" / f"{family}-{subset}-{weight}-normal.woff"
        font = TTFont(source)
        font.flavor = None  # WOFF to plain TrueType
        part = work / f"{name}-{subset}.ttf"
        font.save(part)
        parts.append(str(part))
    target = OUT / f"{name}.ttf"
    Merger().merge(parts).save(target)
    return target


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        for name, (family, weight) in FONTS.items():
            target = build(name, family, weight, Path(folder))
            glyphs = len(TTFont(target).getBestCmap())
            print(f"{target.relative_to(ROOT)}: {glyphs} characters")


if __name__ == "__main__":
    main()
