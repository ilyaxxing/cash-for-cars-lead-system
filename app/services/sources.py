"""Lead source labels: where the seller found the form.

The business card QR code points at /v, which tags the visit as "card". Any
other placement uses its own ?src= label (a parking lot sticker, a flyer)
and gets a readable name through SOURCE_LABELS.

Two rules carried over from the Telegram bot:
- The first meaningful source wins. A later visit with a label only replaces
  the default "direct", never another label: someone who scanned the business
  card and later came back by a typed address still counts as "card".
- The lead keeps the source it had when it was created. Statistics group by
  it, so past months never shift.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping

from app.db.models import DEFAULT_SOURCE
from app.i18n import Messages

logger = logging.getLogger(__name__)

CARD_SOURCE = "card"
SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_warned: set[str] = set()


def parse_source(raw: str | None) -> str | None:
    """A clean source label, or None when there is none or it is junk."""
    if not raw:
        return None
    candidate = raw.strip()
    if not SOURCE_RE.match(candidate):
        return None
    return candidate.lower()


def choose_source(stored: str | None, incoming: str | None) -> str:
    """Which source to remember after a visit: the first meaningful one wins."""
    if incoming and (not stored or stored == DEFAULT_SOURCE):
        return incoming
    return stored or DEFAULT_SOURCE


def source_label(source: str, custom_labels: Mapping[str, str], messages: Messages) -> str:
    """Readable name for a source.

    A label nobody described shows up as "Other" instead of raw junk such as
    test labels, but it is logged once, so a forgotten SOURCE_LABELS entry
    does not disappear without a trace.
    """
    if source in custom_labels:
        return custom_labels[source]
    key = f"sources.{source}"
    if messages.has(key):
        return messages.t(key)
    if source not in _warned:
        _warned.add(source)
        logger.warning("Source %r has no label in SOURCE_LABELS; shown as Other", source)
    return messages.t("sources.other")
