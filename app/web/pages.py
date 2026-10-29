"""Serving the two single-page apps with their configuration baked in.

The built index.html files contain a <!--app-config--> marker. It is replaced
with the client's accent color as CSS variables and a JSON data block
(brand, preset, texts), so the page renders in its final colors without an
extra request. During frontend development Vite serves the HTML itself and
the app fetches the same data from /api/config instead.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from app.services.retention import RETENTION_DAYS
from app.services.sources import CARD_SOURCE
from app.services.validation import format_phone

router = APIRouter()

CONFIG_MARKER = "<!--app-config-->"


def public_config(request: Request) -> dict[str, Any]:
    """What the browser may know about this instance. No secrets, ever."""
    settings = request.app.state.settings
    preset = request.app.state.preset
    return {
        "brand": {
            "name": settings.brand_name,
            "phone": format_phone(settings.brand_phone, preset.phone_region),
            **request.app.state.brand.public(),
        },
        # Named in the consent text: the business that receives the data.
        "operator": settings.operator_name or settings.brand_name,
        "locale": settings.locale,
        "currency": settings.currency,
        "timezone": settings.timezone,
        "preset": preset.model_dump(mode="json", exclude_none=True),
        "messages": request.app.state.messages.data,
        "privacyUrl": "/privacy",
        "retentionDays": RETENTION_DAYS,
    }


def config_block(config: dict[str, Any]) -> str:
    # Escaping <, > and & keeps text from the preset or locale from closing
    # the script element early.
    payload = (
        json.dumps(config, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return f'<script id="app-config" type="application/json">{payload}</script>'


def read_template(path: Path) -> str | None:
    try:
        modified = path.stat().st_mtime_ns
    except FileNotFoundError:
        return None
    return _read_cached(path, modified)


@lru_cache(maxsize=8)
def _read_cached(path: Path, modified: int) -> str:
    # Keyed by modification time: a rebuilt frontend is picked up without a restart.
    return path.read_text(encoding="utf-8")


# Each page's name in a browser tab or on an iPhone's home screen bookmark.
PAGE_TITLES = {"index.html": "form.page_title", "app/index.html": "dashboard.leads.title"}


def render_page(request: Request, relative: str) -> Response:
    template = read_template(request.app.state.settings.frontend_dist / relative)
    if template is None:
        return PlainTextResponse(
            "Frontend is not built. Run `npm run build` in frontend/.", status_code=503
        )
    head = request.app.state.brand.palette.style() + config_block(public_config(request))
    html = template.replace(CONFIG_MARKER, head, 1)
    # The built pages say English; the client's language and country go in
    # instead ("tr-TR"), which also picks the right capitals and characters.
    state = request.app.state
    locale = escape(f"{state.settings.locale}-{state.preset.phone_region}")
    html = html.replace('<html lang="en">', f'<html lang="{locale}">', 1)
    title = escape(state.messages.t(PAGE_TITLES[relative]))
    html = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{title}</title>", html, count=1)
    # Always revalidate: the HTML is tiny and must point at the current bundle.
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


@router.get("/api/config", include_in_schema=False)
async def api_config(request: Request) -> JSONResponse:
    return JSONResponse(public_config(request))


@router.get("/", include_in_schema=False)
async def seller_form(request: Request) -> Response:
    return render_page(request, "index.html")


@router.get("/v", include_in_schema=False)
async def business_card(request: Request) -> RedirectResponse:
    """Short link printed as the QR code on business cards.

    Kept short on purpose: fewer characters mean a smaller QR matrix and
    larger modules, which matters at business card size.
    """
    return RedirectResponse(f"/?src={CARD_SOURCE}", status_code=302)


# Plain def: the icon addresses carry their hashes, and the first call may
# draw the icons (see app/web/brand.py).
@router.get("/app/manifest.webmanifest", include_in_schema=False)
def manifest(request: Request) -> JSONResponse:
    """Web app manifest: makes the dashboard installable under the client's brand."""
    name = request.app.state.settings.brand_name
    icon = request.app.state.brand.icon_url
    return JSONResponse(
        {
            "name": name,
            "short_name": name if len(name) <= 12 else name.split()[0][:12],
            "start_url": "/app/",
            "scope": "/app/",
            "display": "standalone",
            "background_color": "#0B0C0C",
            "theme_color": "#0B0C0C",
            "icons": [
                {"src": icon("icon-192.png"), "sizes": "192x192", "type": "image/png"},
                {"src": icon("icon-512.png"), "sizes": "512x512", "type": "image/png"},
                {
                    "src": icon("maskable-512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
        },
        media_type="application/manifest+json",
    )


@router.get("/app/sw.js", include_in_schema=False)
async def service_worker(request: Request) -> Response:
    path = request.app.state.settings.frontend_dist / "app" / "sw.js"
    if not path.exists():
        return PlainTextResponse("Frontend is not built.", status_code=503)
    # Never cached by the browser: an updated worker must be picked up at once.
    return FileResponse(
        path,
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/app/"},
    )


@router.get("/app", include_in_schema=False)
@router.get("/app/{path:path}", include_in_schema=False)
async def dashboard(request: Request, path: str = "") -> Response:
    return render_page(request, "app/index.html")
