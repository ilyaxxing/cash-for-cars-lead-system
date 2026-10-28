"""Delivering queued notifications.

Events are written to notification_outbox together with the change that
caused them. A background task in the app sends whatever is due through
every configured channel, waking up at once when something is queued and
every few seconds otherwise.

Retries: a failed delivery is tried again after 1, 5, 15 and 60 minutes,
then marked failed. An event with no device to deliver to is "skipped": the
dashboard shows a warning about it instead of retrying forever.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from contextlib import suppress
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models import Lead, OutboxEvent, Photo
from app.i18n import Messages
from app.notify import Channel, build

logger = logging.getLogger(__name__)

RETRY_DELAYS = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
)
POLL_SECONDS = 15
BATCH = 20


def enqueue(session: AsyncSession, lead_id: int, kind: str) -> None:
    """Queue a notification; it is sent once the caller commits."""
    session.add(OutboxEvent(lead_id=lead_id, kind=kind))


async def process_due(
    sessions: async_sessionmaker[AsyncSession],
    channels: Sequence[Channel],
    messages: Messages,
    settings: Settings,
    now: datetime,
    region: str = "US",
) -> int:
    """Send every due event once. Returns how many were handled."""
    async with sessions() as session:
        events = list(
            await session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending", OutboxEvent.next_attempt_at <= now)
                .order_by(OutboxEvent.id)
                .limit(BATCH)
                .with_for_update(skip_locked=True)
            )
        )
        for event in events:
            await _deliver(session, event, channels, messages, settings, now, region)
        await session.commit()
        return len(events)


async def _deliver(
    session: AsyncSession,
    event: OutboxEvent,
    channels: Sequence[Channel],
    messages: Messages,
    settings: Settings,
    now: datetime,
    region: str,
) -> None:
    lead = await session.get(Lead, event.lead_id)
    if lead is None:
        event.status = "skipped"
        return
    photos = await session.scalar(select(func.count()).where(Photo.lead_id == lead.id)) or 0
    notification = build(event.kind, lead, photos, messages, settings, region)

    event.attempts += 1
    delivered = retry = 0
    for channel in channels:
        try:
            result = await channel.send(notification)
        except Exception:
            logger.exception("Channel %s failed on event %s", channel.name, event.id)
            retry += 1
            continue
        delivered += result.delivered
        retry += result.retry

    if delivered:
        event.status = "sent"
        event.sent_at = now
        event.last_error = None
    elif retry and event.attempts <= len(RETRY_DELAYS):
        event.next_attempt_at = now + RETRY_DELAYS[event.attempts - 1]
        event.last_error = "delivery failed, will retry"
    elif retry:
        event.status = "failed"
        event.last_error = "delivery failed, gave up"
        logger.error("Notification %s for lead %s could not be delivered", event.id, lead.id)
    else:
        event.status = "skipped"
        event.last_error = "no device to deliver to"
        logger.warning("Notification %s for lead %s: no device subscribed", event.id, lead.id)


async def run(
    sessions: async_sessionmaker[AsyncSession],
    channels: Sequence[Channel],
    messages: Messages,
    settings: Settings,
    region: str,
    wakeup: asyncio.Event,
) -> None:
    """The background loop. Stops when its task is cancelled."""
    from app.services.leads import utcnow

    logger.info(
        "Notification worker started: %s", ", ".join(c.name for c in channels) or "no channels"
    )
    while True:
        try:
            while await process_due(sessions, channels, messages, settings, utcnow(), region):
                pass
        except Exception:
            # A database hiccup must not kill the loop; try again on the next tick.
            logger.exception("Notification worker pass failed")
        wakeup.clear()
        with suppress(TimeoutError):
            await asyncio.wait_for(wakeup.wait(), timeout=POLL_SECONDS)
