"""Turn photo-guide sketches into the form's dark guide images.

    .venv/bin/python tools/make_guides.py

Reads design-reference/guide-<slot>.(png|jpg): pencil sketches, dark lines on
light paper. Writes frontend/src/assets/illustrations/guide-<slot>.webp, the
names the preset refers to.

The form is dark, so a sketch on white paper would sit in the tile as a white
card. Each image is redrawn in two colors instead: the paper becomes exactly
the empty tile's background, the pencil becomes a soft light line, and every
gray in between is blended between the two. The tile and the drawing then
read as one surface, with no visible edge.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "design-reference"
OUT = ROOT / "frontend" / "src" / "assets" / "illustrations"

# --surface-sunken and a line between --text-soft and --text-muted
# (frontend/src/shared/base.css).
PAPER = (22, 23, 23)
INK = (190, 189, 183)
# Long side of the output: sharp on a phone at 3x, small enough to load fast.
LONG_SIDE = 1100
# Paper texture and JPEG noise below this share of full ink count as paper.
NOISE = 0.07
# Average ink coverage of an outline sketch. Interior sketches are mostly
# solid fills; turned light they would glare next to the outlines, so their
# lines are dimmed until the image carries about this much light.
TARGET_COVERAGE = 0.2
MIN_STRENGTH = 0.55
QUALITY = 78


def recolor(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    # The paper's own brightness, measured rather than assumed: scans and
    # renders are rarely pure white.
    histogram = gray.histogram()
    total, seen, paper = sum(histogram), 0, 255
    for level in range(255, -1, -1):
        seen += histogram[level]
        if seen >= total * 0.02:
            paper = level
            break

    def ink_share(level: int) -> float:
        share = max(0.0, min(1.0, (paper - level) / max(paper, 1)))
        if share < NOISE:
            return 0.0
        # Lift faint hatching a little so it survives on the dark tile.
        return share**0.85

    coverage = sum(ink_share(level) * count for level, count in enumerate(histogram)) / total
    strength = max(MIN_STRENGTH, min(1.0, TARGET_COVERAGE / max(coverage, 1e-6)))

    tables = []
    for low, high in zip(PAPER, INK, strict=True):
        tables += [round(low + (high - low) * strength * ink_share(level)) for level in range(256)]
    return Image.merge("RGB", (gray, gray, gray)).point(tables)


def main() -> None:
    sources = sorted(SOURCE.glob("guide-*.png")) + sorted(SOURCE.glob("guide-*.jpg"))
    if not sources:
        raise SystemExit(f"No guide-<slot>.png or .jpg in {SOURCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sources:
        image = recolor(Image.open(path))
        image.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)
        target = OUT / f"{path.stem}.webp"
        image.save(target, "WEBP", quality=QUALITY, method=6)
        print(
            f"{target.relative_to(ROOT)}  {image.width}x{image.height}  "
            f"{target.stat().st_size // 1024} KB"
        )


if __name__ == "__main__":
    main()
