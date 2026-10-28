"""Build the site installers send car buyers to, into a folder.

    .venv/bin/python tools/make_buyer_site.py OUT

The page for car buyers (buyer-site/index.html) goes to the root, with the
live demo (docs/demo) and the fonts and card pictures it shows. It is
published apart from the project page, on a site of its own (a GitHub
organization's <name>.github.io): a buyer who shortens the address must not
land on the installers' page with its prices. Run tools/make_demo.py first
when the form or the dashboard changed; this only gathers what is built.

OUT may be a clone of the site's repository: everything in it except .git is
replaced, then commit and push there (docs/README.md).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
# Shared with the project page: the fonts and the sample card in six colors.
ASSETS = ("fonts", "card")


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for entry in out.iterdir():
        if entry.name == ".git":
            continue
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    shutil.copy(ROOT / "buyer-site" / "index.html", out / "index.html")
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
