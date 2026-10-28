"""Web Push channel (VAPID).

Payloads are encrypted end to end (RFC 8291): the push services that relay
them cannot read them. They hold no personal data anyway.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models import PushSubscription
from app.notify import Delivery, Notification

logger = logging.getLogger(__name__)

# Push services browsers use today. Subscriptions pointing anywhere else are
# refused: the server would otherwise POST to any address it is given.
PUSH_HOSTS = (
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "push.services.mozilla.com",
    "web.push.apple.com",
    "notify.windows.com",
)
# A day: a phone that was off overnight still gets the lead in the morning.
TTL_SECONDS = 24 * 60 * 60
GONE = (404, 410)


def allowed_endpoint(endpoint: str) -> bool:
    parts = urlsplit(endpoint)
    host = parts.hostname or ""
    return parts.scheme == "https" and any(
        host == known or host.endswith(f".{known}") for known in PUSH_HOSTS
    )


def send_webpush(subscription: dict[str, Any], payload: str, settings: Settings) -> None:
    """One push, blocking. Kept separate so tests can replace it."""
    webpush(
        subscription_info=subscription,
        data=payload,
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": settings.vapid_subject or settings.resolved_public_url},
        ttl=TTL_SECONDS,
        headers={"Urgency": "high"},
        timeout=10,
    )


def utcnow() -> datetime:
    from app.services.leads import utcnow as now

    return now()


class PushChannel:
    name = "push"

    def __init__(self, settings: Settings, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.settings = settings
        self.sessions = sessions

    async def send(self, notification: Notification, endpoint: str | None = None) -> Delivery:
        payload = json.dumps(
            {
                "title": notification.title,
                "body": notification.body,
                "url": notification.url,
                "tag": notification.tag,
            }
        )
        result = Delivery()
        async with self.sessions() as session:
            query = select(PushSubscription)
            if endpoint:
                query = query.where(PushSubscription.endpoint == endpoint)
            for subscription in list(await session.scalars(query)):
                info = {
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                }
                try:
                    await asyncio.to_thread(send_webpush, info, payload, self.settings)
                except WebPushException as exc:
                    status = exc.response.status_code if exc.response is not None else None
                    if status in GONE:
                        # The browser dropped the subscription (app removed,
                        # permission revoked): it will never work again.
                        await session.execute(
                            delete(PushSubscription).where(PushSubscription.id == subscription.id)
                        )
                        logger.info("Push subscription %s is gone, removed", subscription.id)
                    else:
                        subscription.failure_count += 1
                        subscription.last_failure_at = utcnow()
                        result.retry = True
                        logger.warning(
                            "Push to subscription %s failed: %s", subscription.id, status
                        )
                    result.failed += 1
                except Exception:
                    subscription.failure_count += 1
                    subscription.last_failure_at = utcnow()
                    result.failed += 1
                    result.retry = True
                    logger.exception("Push to subscription %s failed", subscription.id)
                else:
                    subscription.failure_count = 0
                    subscription.last_success_at = utcnow()
                    result.delivered += 1
            await session.commit()
        return result
