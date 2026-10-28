"""Telling the owner about new leads.

A notification says which car arrived and for what price. It never carries
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
from app.i18n import Messages, format_money


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
) -> Notification:
    """The notification for an event. Only the car and the price, by design.

    region is the preset's country, for how the price is written.
    """
    if lead.asking_price is not None:
        price = format_money(lead.asking_price, settings.currency, settings.locale, region)
    else:
        price = messages.t("notifications.no_price")
    if photo_count == 0:
        photos = messages.t("notifications.no_photos")
    elif photo_count == 1:
        photos = messages.t("notifications.photos_one")
    else:
        photos = messages.t("notifications.photos_other", count=photo_count)
    if kind not in (EVENT_NEW_LEAD, EVENT_PHOTOS_ADDED):
        raise ValueError(f"unknown notification kind {kind!r}")
    car = car_name(lead, messages)
    return Notification(
        title=messages.t(f"notifications.{kind}.title", car=car),
        body=messages.t(f"notifications.{kind}.body", price=price, photos=photos),
        url=f"/app/leads/{lead.id}",
        tag=f"lead-{lead.id}",
    )


def test_notification(messages: Messages, settings: Settings) -> Notification:
    return Notification(
        title=messages.t("notifications.test.title", brand=settings.brand_name),
        body=messages.t("notifications.test.body"),
        url="/app/settings",
        tag="test",
    )
