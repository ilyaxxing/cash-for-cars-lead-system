"""Retention of sellers' personal data.

The only place the period is set. Name, phone, the other personal answers
(fields marked `personal: true` in the preset) and the photos are needed
while the deal is alive; once the lead is closed (purchased or rejected)
they become a liability, so they are erased RETENTION_DAYS later. The car
and the outcome stay for statistics. Photos go too: a plate, a face or a
driveway in the background identifies the seller as well as a name does.

The period counts from closing, not from arrival: buyers call old leads back,
and a lead that took three months to close must not lose its phone number the
day it closes.

What this cannot reach, and the privacy policy says so: database backups
until their own rotation, notifications already shown on the owner's phone,
and calls and chats on both sides. If the period is shortened, the real
period is still no shorter than the backup rotation, or the policy lies.

The pass runs at startup (an app that was down catches up at once) and then
daily. It writes one log line per pass even when nothing was erased: that
line is the only proof the job is alive. A failure is logged as an error and
never stops the app; the next pass tries again.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.db.models import CLOSED_STATUSES, Lead
from app.preset.schema import Preset
from app.services.answers import personal_fields
from app.storage import Storage

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90
PASS_INTERVAL = timedelta(days=1)
BATCH = 200


@dataclass
class PassResult:
    leads: int = 0
    photos: int = 0
    # Leads whose photos could not all be deleted from storage. They keep
    # purged_at empty, so the next pass picks them up again.
    retry: int = 0


async def purge_expired(
    sessions: async_sessionmaker[AsyncSession],
    preset: Preset,
    storage: Storage,
    now: datetime | None = None,
) -> PassResult:
    """Erase personal data of leads closed more than RETENTION_DAYS ago."""
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=RETENTION_DAYS)
    personal = set(personal_fields(preset))
    result = PassResult()
    last_id = 0
    while True:
        async with sessions() as session:
            leads = list(
                await session.scalars(
                    select(Lead)
                    .where(
                        Lead.id > last_id,
                        Lead.status.in_(CLOSED_STATUSES),
                        Lead.closed_at <= cutoff,
                        Lead.purged_at.is_(None),
                    )
                    .order_by(Lead.id)
                    .limit(BATCH)
                    .options(selectinload(Lead.photos))
                    .with_for_update(of=Lead, skip_locked=True)
                )
            )
            if not leads:
                return result
            for lead in leads:
                last_id = lead.id
                photos_left = await _erase(lead, personal, storage, now, result)
                if photos_left:
                    result.retry += 1
                else:
                    lead.purged_at = now
                    result.leads += 1
            await session.commit()


async def _erase(
    lead: Lead, personal: set[str], storage: Storage, now: datetime, result: PassResult
) -> int:
    lead.name = None
    lead.phone = None
    if personal & lead.answers.keys():
        # A new dict, not an in-place edit: SQLAlchemy only notices reassignment.
        lead.answers = {key: value for key, value in lead.answers.items() if key not in personal}
    left = 0
    for photo in list(lead.photos):
        try:
            # Objects first, then the row: a row without its object is
            # harmless, an object without a row would never be found again.
            await storage.delete(photo.thumb_key)
            await storage.delete(photo.key)
        except Exception:
            logger.exception("Retention: photo %s of lead %s not deleted", photo.id, lead.id)
            left += 1
            continue
        lead.photos.remove(photo)
        result.photos += 1
    return left


async def run(sessions: async_sessionmaker[AsyncSession], preset: Preset, storage: Storage) -> None:
    """The daily pass. Stops when its task is cancelled."""
    logger.info(
        "Retention: personal data is erased %s days after a lead is closed, checked daily",
        RETENTION_DAYS,
    )
    while True:
        try:
            result = await purge_expired(sessions, preset, storage)
            if result.leads or result.photos or result.retry:
                logger.info(
                    "Retention pass: erased %s leads, %s photos; %s leads left for the next pass",
                    result.leads,
                    result.photos,
                    result.retry,
                )
            else:
                logger.info("Retention pass: nothing to erase")
        except Exception:
            logger.exception("Retention pass failed; the next one runs in a day")
        await asyncio.sleep(PASS_INTERVAL.total_seconds())
