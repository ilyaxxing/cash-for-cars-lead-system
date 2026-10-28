"""QR codes for business cards, stickers and flyers.

    python -m app.cli qr                       business card: <PUBLIC_URL>/v
    python -m app.cli qr --source parking      any other placement: <PUBLIC_URL>/?src=parking

Writes an SVG for the print shop (vector, sharp at any size) and a PNG
preview for messengers into qr/, which is git-ignored: the files carry the
client's address.

A mistake here shows up on paper, after the print run, so the print
parameters live in this one place and the code is checked before it is
written:
- Error correction H. It survives up to 30% damage: a business card lives
  in a pocket, gets worn and bent.
- A quiet zone of 4 modules is part of the standard. Designers like to crop
  it, and then phones stop reading the code.
- The PNG uses a whole number of pixels per module: a fractional scale blurs
  the edges and hurts reading.
- A printed module must stay at or above MIN_MODULE_MM. A longer address
  needs a bigger matrix, so the same 20 mm code gets finer modules; below
  the limit phones still read it, but slowly, and a person at the counter
  will not wait.
- The address is printed for good, so it must be the client's own domain.
  The Railway address (`*.up.railway.app`) is tied to one Railway project
  and is not the business's own: the generator refuses it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import segno

from app.services.sources import CARD_SOURCE, SOURCE_RE

ERROR_LEVEL = "h"
BORDER = 4
# Smallest printed module that still reads instantly, in millimeters.
MIN_MODULE_MM = 0.4
# Side of the code on a business card, without the quiet zone.
DEFAULT_SIZE_MM = 20.0
PNG_SCALE = 10
RAILWAY_HOSTS = (".up.railway.app",)


@dataclass
class Plan:
    url: str
    modules: int = 0
    module_mm: float = 0.0
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def link(base_url: str, source: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/v" if source == CARD_SOURCE else f"{base}/?src={source}"


def code(url: str) -> segno.QRCode:
    # make_qr, not make: a short address must never become a Micro QR,
    # which most phone cameras cannot read.
    return segno.make_qr(url, error=ERROR_LEVEL, boost_error=False)


def plan(
    base_url: str,
    source: str,
    *,
    size_mm: float = DEFAULT_SIZE_MM,
    labels: Mapping[str, str] | None = None,
) -> Plan:
    """Check a code before anything is written."""
    result = Plan(url=link(base_url, source))
    parts = urlsplit(base_url)
    if parts.scheme != "https" or not parts.hostname:
        result.problems.append(f"PUBLIC_URL must be the public https:// address, got {base_url!r}")
        return result
    if not SOURCE_RE.match(source) or source != source.lower():
        result.problems.append(
            f"Source {source!r}: use lowercase letters, digits, dash and underscore only"
        )
        return result

    result.modules = code(result.url).symbol_size(scale=1, border=0)[0]
    result.module_mm = size_mm / result.modules
    if result.module_mm < MIN_MODULE_MM:
        result.problems.append(
            f"At {size_mm:g} mm a module is {result.module_mm:.2f} mm, under the "
            f"{MIN_MODULE_MM} mm print limit. Print it larger (--size-mm), or use a "
            "shorter domain or source label."
        )
    if parts.hostname.endswith(RAILWAY_HOSTS):
        result.problems.append(
            f"{parts.hostname} is the Railway address. Printed codes must point at the "
            "client's own domain: connect it first and set PUBLIC_URL (or --url) to it "
            "(docs/deploy.md, Custom domain)."
        )
        return result
    if source != CARD_SOURCE and source not in (labels or {}):
        result.warnings.append(
            f"The dashboard will show {source!r} as Other. Add it to SOURCE_LABELS, "
            f"for example SOURCE_LABELS={source}:Parking lot"
        )
    return result


def write(checked: Plan, out_dir: Path) -> tuple[Path, Path]:
    """Save the print SVG and the PNG preview. Only for a plan without problems."""
    if checked.problems:
        raise ValueError("; ".join(checked.problems))
    symbol = code(checked.url)
    parts = urlsplit(checked.url)
    source = CARD_SOURCE if parts.path == "/v" else parts.query.removeprefix("src=")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{parts.hostname}-{source}"
    svg, png = out_dir / f"{stem}.svg", out_dir / f"{stem}.png"
    symbol.save(svg, scale=PNG_SCALE, border=BORDER)
    symbol.save(png, scale=PNG_SCALE, border=BORDER)
    return svg, png
