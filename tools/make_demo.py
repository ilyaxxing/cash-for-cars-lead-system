"""Build the live demo on the project page (docs/demo).

    .venv/bin/python tools/make_demo.py

The real seller form and owner dashboard, built from frontend/ with a
stand-in for the server that runs in the browser (frontend/src/demo):
visitors try both on GitHub Pages and nothing they type leaves the page.
The HTML comes from the app itself, as a client's instance serves it, with
the default brand and a fictional business. Run it again after changing the
form or the dashboard, and commit docs/demo.
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Only the HTML is fetched through the test client; its httpx notice is noise here.
warnings.filterwarnings("ignore", message="Using `httpx`")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

OUT = ROOT / "docs" / "demo"
# A fictional business: the consent text and the privacy policy name it.
BUSINESS = {
    "brand_phone": "(512) 555-0100",
    "operator_name": "Example Auto LLC",
    "operator_email": "privacy@example.com",
    "operator_address": "100 Example St, Austin, TX 78701",
    "policy_effective_date": "October 1, 2026",
    "public_url": "https://buy.example.com",
    "timezone": "America/Chicago",
}
PAGES = {"index.html": "/", "app/index.html": "/app/", "privacy.html": "/privacy"}


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


def demo_page(html: str, script: str, depth: int) -> str:
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
    tag = f'<script type="module" crossorigin src="{up}{script}"></script>\n    '
    return html[:first] + tag + html[first:]


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        dist = Path(temp) / "dist"
        script = build(dist)
        settings = Settings(
            _env_file=None, app_env="development", log_level="ERROR", frontend_dist=dist, **BUSINESS
        )
        client = TestClient(create_app(settings))
        pages = {}
        for name, path in PAGES.items():
            response = client.get(path)
            response.raise_for_status()
            pages[name] = response.text

        if OUT.exists():
            shutil.rmtree(OUT)
        shutil.copytree(dist / "assets", OUT / "assets")
        shutil.copy(dist / "brand.js", OUT / "brand.js")
        (OUT / "app").mkdir(parents=True)
        for name in ("index.html", "app/index.html"):
            text = demo_page(pages[name], script, name.count("/"))
            (OUT / name).write_text(text, encoding="utf-8")
        policy = pages["privacy.html"].replace('<a href="/">', '<a href="index.html">', 1)
        # The demo script puts a named business's name and color in here too.
        policy = policy.replace(
            '<meta charset="utf-8">',
            '<meta charset="utf-8">\n<meta name="robots" content="noindex">\n'
            f'<script type="module" crossorigin src="./{script}"></script>',
            1,
        )
        (OUT / "privacy.html").write_text(policy, encoding="utf-8")

    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"demo:    {OUT.relative_to(ROOT)}/ ({size // 1024} KB)")


if __name__ == "__main__":
    main()
