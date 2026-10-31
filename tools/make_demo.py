"""Build the live demo (docs/demo), one per country in countries/.

    .venv/bin/python tools/make_demo.py

The real seller form and owner dashboard, built from frontend/ with a
stand-in for the server that runs in the browser (frontend/src/demo):
visitors try both on GitHub Pages and nothing they type leaves the page.
The HTML comes from the app itself, as a client's instance serves it, with
each country's settings (countries/<code>/settings.env) and a fictional
business with its leads (countries/<code>/demo.yaml). The United States is
docs/demo itself, which the project page shows; every other country is
docs/demo/<code>/. The sample business cards for the page sent to car
buyers are drawn here too (docs/assets/card/<code>/). Run it again after
changing the form, the dashboard or a country, and commit docs/.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Only the HTML is fetched through the test client; its httpx notice is noise here.
warnings.filterwarnings("ignore", message="Using `httpx`")

from fastapi.testclient import TestClient  # noqa: E402

from app.branding import card as cards  # noqa: E402
from app.branding.colors import Palette  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

OUT = ROOT / "docs" / "demo"
COUNTRIES = ROOT / "countries"
CARDS = ROOT / "docs" / "assets" / "card"
# The country at docs/demo itself, the one the project page shows.
DEFAULT = "us"
PAGES = {"index.html": "/", "app/index.html": "/app/", "privacy.html": "/privacy"}
# What demo.yaml's business sets as settings; the rest is for the demo only.
SETTINGS = (
    "brand_name",
    "brand_phone",
    "operator_name",
    "operator_email",
    "operator_address",
    "policy_effective_date",
    "public_url",
)
# The sample card's colors on the page for car buyers, as its link maker offers them.
CARD_COLORS = {
    "lime": "#C7F747",
    "orange": "#FF8A00",
    "yellow": "#FFD60A",
    "red": "#FF4D4D",
    "blue": "#3DA5FF",
    "mint": "#3DDC97",
}
# Every made-up person and number is in this one line of each page.
DATA_TAG = '<script id="demo-data" type="application/json">{}</script><!-- pii-allow: demo -->'


def build(dist: Path) -> str:
    """The frontend in demo mode; returns the demo script's path in dist."""
    subprocess.run(
        [
            "npm",
            "run",
            "--silent",
            "build",
            "--",
            "--mode",
            "demo",
            "--logLevel",
            "warn",
            "--outDir",
            str(dist),
        ],
        cwd=ROOT / "frontend",
        check=True,
    )
    manifest = json.loads((dist / ".vite" / "manifest.json").read_text(encoding="utf-8"))
    # A fixed address for the static pages' imports (the page for car buyers,
    # the link maker on the project page); the bundle itself is hashed.
    brand = manifest["src/demo/brand.ts"]["file"]
    (dist / "brand.js").write_text(f'export * from "./{brand}";\n', encoding="utf-8")
    return manifest["src/demo/main.ts"]["file"]


def country_codes() -> list[str]:
    codes = sorted(path.name for path in COUNTRIES.iterdir() if (path / "demo.yaml").is_file())
    return [DEFAULT, *(code for code in codes if code != DEFAULT)]


def load_demo(code: str) -> dict[str, Any]:
    return yaml.safe_load((COUNTRIES / code / "demo.yaml").read_text(encoding="utf-8"))


def settings_for(code: str, dist: Path) -> Settings:
    demo = load_demo(code)
    return Settings(
        _env_file=COUNTRIES / code / "settings.env",
        app_env="development",
        log_level="ERROR",
        frontend_dist=dist,
        **{key: demo["business"][key] for key in SETTINGS},
    )


def page_data(demo: dict[str, Any], settings: Settings, distance_unit: str) -> str:
    """The country's part of the demo, as frontend/src/demo/seed.ts reads it."""
    data = {
        "business_names": [demo["business"]["operator_name"], settings.brand_name],
        "sources": demo["sources"],
        "calls_off": demo["calls_off"],
        "price_scale": demo["price_scale"],
        "price_step": demo["price_step"],
        "distance_unit": distance_unit,
        **{key: demo[key] for key in ("featured", "phones", "cars", "names", "cities")},
        "extra": demo.get("extra", {}),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return DATA_TAG.format(payload.replace("<", "\\u003c"))


def deeper(html: str, levels: int) -> str:
    """A page moved `levels` folders down still finds the shared assets."""
    if not levels:
        return html

    def up(match: re.Match[str]) -> str:
        extra = "../" if match[2] == "../" else ""
        return match[1] + "../" * levels + extra

    return re.sub(r'((?:src|href)=")(\.\.?/)', up, html)


def demo_page(html: str, script: str, depth: int, data: str) -> str:
    """A page as the app served it, made to run from a folder of static files."""
    up = "../" * depth or "./"
    # No home-screen install: the icons and the manifest are drawn by a server.
    html = re.sub(r'\s*<link rel="(?:icon|manifest|apple-touch-icon)"[^>]*>', "", html)
    html = html.replace(
        '<meta charset="utf-8" />',
        '<meta charset="utf-8" />\n    <meta name="robots" content="noindex" />',
        1,
    )
    # The stand-in server goes first, so it is there for the app's first request.
    first = html.index('<script type="module"')
    tag = f'{data}\n    <script type="module" crossorigin src="{up}{script}"></script>\n    '
    return html[:first] + tag + html[first:]


def policy_page(html: str, script: str, depth: int, data: str, note: str) -> str:
    html = html.replace('<a href="/">', '<a href="index.html">', 1)
    # The demo script puts a named business's name and color in here too.
    html = html.replace(
        '<meta charset="utf-8">',
        f'<meta charset="utf-8">\n<meta name="robots" content="noindex">\n{data}\n'
        f'<script type="module" crossorigin src="{"../" * depth or "./"}{script}"></script>',
        1,
    )
    # Marked as a sample: a real business's policy follows its country's law.
    note_html = (
        '<p style="margin:24px 0 0;padding:12px 14px;border-radius:12px;'
        'background:rgb(255 255 255 / .06);color:#A5A7A2;font-size:14px">'
        f"{note}</p>"
    )
    return html.replace("</header>", "</header>\n" + note_html, 1)


def draw_cards(code: str, settings: Settings, demo: dict[str, Any], messages: Any) -> None:
    """The sample card in each of the page's six colors, front and back."""
    out = CARDS if code == DEFAULT else CARDS / code
    out.mkdir(parents=True, exist_ok=True)
    texts = {
        key: messages.t(f"card.{key}") for key in cards.TEXT_KEYS if messages.has(f"card.{key}")
    }
    warnings = set()
    for name, color in CARD_COLORS.items():
        text = cards.CardText(
            brand_name=settings.brand_name,
            accent=cards.accent_ink(Palette.from_hex(color).accent),
            base_url=demo["business"]["public_url"],
            phone=demo["business"]["brand_phone"],
            name=demo["business"]["card_contact"],
            texts=texts,
            format=cards.card_format(settings.card_size),
            font=settings.card_font,
            locale=settings.locale,
        )
        made = cards.make(text)
        warnings.update(made.warnings)
        for side, ops in (("front", made.front), ("back", made.back)):
            image = cards.render(ops, made.format, dpi=288)
            image.save(out / f"{name}-{side}.webp", quality=90, method=6)
    for warning in sorted(warnings):
        print(f"WARNING: {code} card: {warning}")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        dist = Path(temp) / "dist"
        script = build(dist)
        if OUT.exists():
            shutil.rmtree(OUT)
        shutil.copytree(dist / "assets", OUT / "assets")
        shutil.copy(dist / "brand.js", OUT / "brand.js")
        for code in country_codes():
            demo = load_demo(code)
            settings = settings_for(code, dist)
            app = create_app(settings)
            client = TestClient(app)
            pages = {}
            for name, path in PAGES.items():
                response = client.get(path)
                response.raise_for_status()
                pages[name] = response.text
            data = page_data(demo, settings, app.state.preset.distance_unit)
            folder = OUT if code == DEFAULT else OUT / code
            levels = 0 if code == DEFAULT else 1
            (folder / "app").mkdir(parents=True, exist_ok=True)
            for name in ("index.html", "app/index.html"):
                text = deeper(demo_page(pages[name], script, name.count("/"), data), levels)
                (folder / name).write_text(text, encoding="utf-8")
            policy = policy_page(pages["privacy.html"], script, levels, data, demo["policy_note"])
            (folder / "privacy.html").write_text(policy, encoding="utf-8")
            draw_cards(code, settings, demo, app.state.messages)
            print(f"country: {code} ({demo['label']})")

    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"demo:    {OUT.relative_to(ROOT)}/ ({size // 1024} KB)")


if __name__ == "__main__":
    main()
