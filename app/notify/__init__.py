"""Telling the owner about new leads.

A notification says which car arrived: its mileage and condition, and the
price and photos once the seller has added them. It never carries
the seller's name, phone number or email: notifications pass through the
push services of Apple, Google and Mozilla and show up on a lock screen.

Channels plug in through CHANNELS: a new way to reach the owner (Telegram,
SMS) is one class with a `send` method and an entry in NOTIFY_CHANNELS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.config import Settings
from app.db.models import EVENT_NEW_LEAD, EVENT_PHOTOS_ADDED, Lead
from app.i18n import Messages, format_money, format_number


@dataclass(frozen=True)
class Notification:
    title: str
    body: str
    url: str
    tag: str


@dataclass
class Delivery:
    """Outcome of one notification on one channel."""

    delivered: int = 0
    failed: int = 0
    # Worth trying again later (a network error, a push service hiccup).
    retry: bool = False

    @property
    def nobody(self) -> bool:
        return not self.delivered and not self.failed


class Channel(Protocol):
    name: str

    async def send(self, notification: Notification) -> Delivery: ...


def car_name(lead: Lead, messages: Messages) -> str:
    if lead.year:
        return messages.t(
            "notifications.car", year=lead.year, make=lead.make, model=lead.model or ""
        )
    return messages.t("notifications.car_no_year", make=lead.make, model=lead.model or "").strip()


def build(
    kind: str,
    lead: Lead,
    photo_count: int,
    messages: Messages,
    settings: Settings,
    region: str = "US",
    distance_unit: str = "mi",
) -> Notification:
    """The notification for an event. Only the car, never the seller, by design.

    A new lead is announced when the seller leaves their contacts, before the
    form asks for the price or the photos. So it says what is known by then,
    the mileage and the condition, and names the price and the photos only
    once they are there.

    region and distance_unit are the preset's, for how numbers are written.
    """
    if kind not in (EVENT_NEW_LEAD, EVENT_PHOTOS_ADDED):
        raise ValueError(f"unknown notification kind {kind!r}")
    price = None
    if lead.asking_price is not None:
        price = format_money(lead.asking_price, settings.currency, settings.locale, region)
    photos = None
    if photo_count == 1:
        photos = messages.t("notifications.photos_one")
    elif photo_count > 1:
        photos = messages.t("notifications.photos_other", count=photo_count)
    if kind == EVENT_NEW_LEAD:
        mileage = None
        if lead.mileage is not None:
            number = format_number(lead.mileage, settings.locale, region)
            mileage = f"{number} {messages.t(f'units.{distance_unit}.short')}"
        known = (mileage, _condition(lead, messages), price, photos)
        body = " · ".join(part for part in known if part)
    else:
        body = messages.t(
            "notifications.photos_added.body",
            photos=photos or messages.t("notifications.no_photos"),
            price=price or messages.t("notifications.no_price"),
        )
    return Notification(
        title=messages.t(f"notifications.{kind}.title", car=car_name(lead, messages)),
        body=body,
        url=f"/app/leads/{lead.id}",
        tag=f"lead-{lead.id}",
    )


def _condition(lead: Lead, messages: Messages) -> str | None:
    """The condition the seller picked, as the form words it; None if not asked."""
    value = (lead.answers or {}).get("condition")
    if not isinstance(value, str):
        return None
    return messages.get(f"preset.options.condition.{value}.label")


def test_notification(messages: Messages, settings: Settings) -> Notification:
    return Notification(
        title=messages.t("notifications.test.title", brand=settings.brand_name),
        body=messages.t("notifications.test.body"),
        url="/app/settings",
        tag="test",
    )
