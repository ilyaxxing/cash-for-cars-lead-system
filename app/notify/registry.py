"""Which channels this instance uses (NOTIFY_CHANNELS)."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.notify import Channel
from app.notify.push import PushChannel

logger = logging.getLogger(__name__)

# A new channel: write a class with `name` and `async send(notification)`,
# add it here, and list its name in NOTIFY_CHANNELS.
CHANNELS = {"push": PushChannel}


class UnknownChannel(Exception):
    pass


def create_channels(
    settings: Settings, sessions: async_sessionmaker[AsyncSession]
) -> list[Channel]:
    channels: list[Channel] = []
    for name in settings.notify_channels:
        if name not in CHANNELS:
            raise UnknownChannel(f"NOTIFY_CHANNELS: unknown channel {name!r}")
        if name == "push" and not settings.push_configured:
            # Development without keys: the app runs, nothing is pushed.
            logger.warning("Push notifications are off: VAPID keys are not set")
            continue
        channels.append(CHANNELS[name](settings, sessions))
    return channels
