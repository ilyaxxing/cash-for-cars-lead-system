"""Build the site installers send car buyers to, into a folder.

    .venv/bin/python tools/make_buyer_site.py OUT

The page for car buyers (buyer-site/index.html, a template) is filled in
for every country in countries/ from its demo.yaml: the United States at
the root, every other country at /<code>/. The live demo (docs/demo) and
the fonts and card pictures the pages show go with them. It is published
apart from the project page, on a site of its own (a GitHub organization's
<name>.github.io): a buyer who shortens the address must not land on the
installers' page with its prices. Run tools/make_demo.py first when the
form, the dashboard or a country changed; this only gathers what is built.

OUT may be a clone of the site's repository: everything in it except .git is
replaced, then commit and push there (docs/README.md).
"""

from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

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


def plain(text: str) -> str:
    """Text for the page, in an element or a double-quoted attribute."""
    return html.escape(text, quote=False).replace('"', "&quot;")


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
    values = {
        **texts,
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
    # Served as it is, never listed by search engines, and a lost address
    # (the dashboard's /app/leads/<id> after a reload) leads back to the page.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
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
