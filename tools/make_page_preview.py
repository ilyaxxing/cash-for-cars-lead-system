"""The link preview of the project page, from the page's own words.

    .venv/bin/python tools/make_page_preview.py
    .venv/bin/python tools/make_page_preview.py --social OUT.jpg

Draws docs/assets/preview.jpg from the kicker and headline of docs/index.html,
the way the page for car buyers draws its own. Run it after changing either.
--social draws the same picture at the size GitHub asks for a repository's
social preview (Settings, Social preview), uploaded by hand.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.make_buyer_site import poster  # noqa: E402
from tools.make_demo import CARDS  # noqa: E402

PAGE = ROOT / "docs" / "index.html"
PICTURE = ROOT / "docs" / "assets" / "preview.jpg"
SOCIAL_SIZE = (1280, 640)


def first_screen() -> tuple[str, str]:
    """The kicker and the headline, as the page shows them."""
    page = PAGE.read_text(encoding="utf-8")
    kicker = re.search(r'<div class="kicker">([^<]+)</div>', page)
    headline = re.search(r"<h1>(.+?)</h1>", page)
    if kicker is None or headline is None:
        raise SystemExit("docs/index.html: no kicker or headline found")
    return html.unescape(kicker.group(1)), html.unescape(headline.group(1))


def main() -> None:
    kicker, headline = first_screen()
    if sys.argv[1:2] == ["--social"] and len(sys.argv) == 3:
        Path(sys.argv[2]).write_bytes(poster(CARDS, kicker, headline, SOCIAL_SIZE))
        print(f"social preview: {sys.argv[2]}")
        return
    if len(sys.argv) > 1:
        raise SystemExit(__doc__)
    PICTURE.write_bytes(poster(CARDS, kicker, headline))
    print(f"preview: {PICTURE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
