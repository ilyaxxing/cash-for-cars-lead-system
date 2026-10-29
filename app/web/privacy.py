"""The privacy policy page, rendered from locales/privacy-policy.<locale>.md.

The template is plain Markdown with {placeholders} filled from the settings.
A line whose placeholders are all empty is dropped, so an instance without a
mailing address simply does not list one instead of printing a blank.

The text is a starting point written for US sellers, not legal advice: the
operator's lawyer should review it before launch.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from markdown_it import MarkdownIt

from app.config import Settings
from app.services.retention import RETENTION_DAYS
from app.services.validation import format_phone

router = APIRouter()

PLACEHOLDER = re.compile(r"\{(\w+)\}")
MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!<>|])")


def _escape_markdown(value: str) -> str:
    return MARKDOWN_SPECIAL.sub(r"\\\1", value)


def fill(template: str, values: dict[str, str]) -> str:
    lines = []
    for line in template.splitlines():
        names = PLACEHOLDER.findall(line)
        if names and not any(values.get(name) for name in names):
            continue
        lines.append(PLACEHOLDER.sub(lambda m: _escape_markdown(values.get(m.group(1), "")), line))
    return "\n".join(lines) + "\n"


def policy_values(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    region = request.app.state.preset.phone_region
    return {
        "operator_name": settings.operator_name or settings.brand_name,
        "brand_name": settings.brand_name,
        "operator_email": settings.operator_email,
        "operator_address": settings.operator_address,
        "brand_phone": format_phone(settings.brand_phone, region),
        "effective_date": settings.policy_effective_date,
        "site_url": settings.resolved_public_url or str(request.base_url).rstrip("/"),
        "retention_days": str(RETENTION_DAYS),
    }


PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#111212">
<title>{title}</title>
{colors}
<style>
html,body{{margin:0;background:#111212;color:#F4F3EE;font-family:Geist,system-ui,sans-serif;
-webkit-font-smoothing:antialiased}}
main{{max-width:720px;margin:0 auto;padding:16px 20px 64px}}
header{{height:44px;display:flex;align-items:center;justify-content:space-between}}
.brand{{display:flex;align-items:center;gap:10px;font:700 14px/1 Geist,sans-serif;
letter-spacing:.14em;text-transform:uppercase}}
.mark{{flex:none;width:22px;height:22px;border-radius:7px;background:var(--accent);
display:flex;align-items:center;justify-content:center}}
.mark svg{{display:block;width:100%;height:100%}}
.mark .tag{{fill:var(--on-accent)}}
.mark .hole{{fill:var(--accent)}}
.logo{{display:block;flex:none;width:auto;height:28px;object-fit:contain}}
.logo.wordmark{{max-width:190px}}
a{{color:#F4F3EE;text-underline-offset:3px;text-decoration-color:#7C7E7A}}
a:hover{{color:var(--accent)}}
header a{{font:500 13.5px/1 Geist,sans-serif;color:#A5A7A2}}
h1{{margin:36px 0 8px;font-size:40px;line-height:1.05;letter-spacing:-0.035em}}
h2{{margin:36px 0 10px;font-size:20px;letter-spacing:-0.02em}}
p,li{{font-size:16px;line-height:1.6;color:#C9C8C2}}
strong{{color:#F4F3EE}}
ul{{padding-left:20px}}
</style>
</head>
<body>
<main>
<header>
<span class="brand">{brand}</span>
<a href="/">{back}</a>
</header>
{body}
</main>
</body>
</html>
"""


# The drawing in the mark: the price tag of frontend/src/shared/TagGlyph.svelte.
TAG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="tag" d="M5 6.8v4.6c0 .5.2 1 '
    ".6 1.4l6.1 6.1c.8.8 2 .8 2.8 0l4.1-4.1c.8-.8.8-2 0-2.8l-6.1-6.1c-.4-.4-.9-.6-1.4-.6H6.8"
    'C5.8 5.3 5 6 5 6.8z"/><circle class="hole" cx="8.4" cy="8.6" r="1.3"/></svg>'
)


def brand_html(name: str, logo: dict[str, Any] | None) -> str:
    """The brand as the apps' headers show it (frontend/src/shared/BrandMark.svelte).

    The client's logo, or the mark in the client's color; the name stands beside
    it unless the logo is a wordmark that already spells it.
    """
    if not logo:
        return f'<span class="mark">{TAG}</span><span>{escape(name)}</span>'
    wordmark = logo["wordmark"]
    alt = escape(name) if wordmark else ""
    image = (
        f'<img class="logo{" wordmark" if wordmark else ""}" src="{escape(logo["url"])}" '
        f'width="{logo["width"]}" height="{logo["height"]}" alt="{alt}">'
    )
    return image if wordmark else f"{image}<span>{escape(name)}</span>"


class PolicyError(Exception):
    """The privacy policy template is missing; raised at startup."""


def check_policy(settings: Settings) -> None:
    """Every page links to the policy, so the app does not start without one."""
    path = settings.privacy_policy_path
    if not path.is_file():
        setting = (
            "PRIVACY_POLICY_FILE" if settings.privacy_policy_file else f"LOCALE={settings.locale!r}"
        )
        raise PolicyError(f"privacy policy {path} not found ({setting})")


@router.get("/privacy", include_in_schema=False)
async def privacy(request: Request) -> HTMLResponse:
    settings = request.app.state.settings
    template = settings.privacy_policy_path.read_text(encoding="utf-8")
    markdown = fill(template, policy_values(request))
    body = MarkdownIt("commonmark", {"html": False}).render(markdown)
    title = markdown.splitlines()[0].lstrip("# ").strip()
    messages = request.app.state.messages
    brand = request.app.state.brand
    html = PAGE.format(
        lang=escape(f"{settings.locale}-{request.app.state.preset.phone_region}"),
        title=escape(title),
        colors=brand.palette.style(),
        brand=brand_html(settings.brand_name, brand.public()["logo"]),
        back=escape(messages.t("privacy.back")),
        body=body,
    )
    return HTMLResponse(html)
