"""Queries behind the owner dashboard: lists, search, counts, notes, events."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    STATUS_IN_WORK,
    STATUS_NEW,
    Lead,
    LeadEvent,
    Note,
    Photo,
)
from app.services.leads import apply_status

TABS: dict[str, tuple[str, ...] | None] = {
    "new": (STATUS_NEW,),
    "in_work": (STATUS_IN_WORK,),
    "all": None,
}
PAGE_SIZE = 60
NOTE_MAX_LENGTH = 1000


def _search(query: str):
    """Every word must match the car, the seller's contact details or the lead id."""
    haystack = func.concat_ws(
        " ",
        Lead.make,
        Lead.model,
        Lead.name,
        Lead.phone,
        Lead.location,
        Lead.answers["email"].astext,
        Lead.answers["vin"].astext,
        cast(Lead.id, String),
    )
    digits = func.regexp_replace(func.coalesce(Lead.phone, ""), r"\D", "", "g")
    conditions = []
    for word in query.split():
        word = word.lstrip("#")
        if not word:
            continue
        clause = haystack.ilike(f"%{word}%")
        # Phone numbers match however they are typed: 415-555, (415) 555, 415555.
        only_digits = re.sub(r"\D", "", word)
        if re.fullmatch(r"[\d()+.\-]+", word) and len(only_digits) >= 3:
            clause = or_(clause, digits.like(f"%{only_digits}%"))
        conditions.append(clause)
    return and_(*conditions) if conditions else None


async def list_leads(
    session: AsyncSession, tab: str, query: str = "", offset: int = 0, limit: int = PAGE_SIZE
) -> tuple[list[Lead], bool]:
    statement = select(Lead)
    statuses = TABS[tab]
    if statuses:
        statement = statement.where(Lead.status.in_(statuses))
    condition = _search(query)
    if condition is not None:
        statement = statement.where(condition)
    statement = statement.order_by(Lead.created_at.desc(), Lead.id.desc()).offset(offset)
    rows = list(await session.scalars(statement.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


async def tab_counts(session: AsyncSession) -> dict[str, int]:
    counts = dict(
        (await session.execute(select(Lead.status, func.count()).group_by(Lead.status))).all()
    )
    return {
        "new": counts.get(STATUS_NEW, 0),
        "in_work": counts.get(STATUS_IN_WORK, 0),
        "all": sum(counts.values()),
    }


async def photos_by_lead(session: AsyncSession, lead_ids: Sequence[int]) -> dict[int, list[Photo]]:
    result: dict[int, list[Photo]] = {lead_id: [] for lead_id in lead_ids}
    if lead_ids:
        rows = await session.scalars(
            select(Photo).where(Photo.lead_id.in_(lead_ids)).order_by(Photo.id)
        )
        for photo in rows:
            result[photo.lead_id].append(photo)
    return result


async def notes_for(session: AsyncSession, lead_id: int) -> list[Note]:
    rows = await session.scalars(
        select(Note)
        .where(Note.lead_id == lead_id, Note.deleted_at.is_(None))
        .order_by(Note.created_at.desc(), Note.id.desc())
    )
    return list(rows)


async def events_for(session: AsyncSession, lead_id: int) -> list[LeadEvent]:
    rows = await session.scalars(
        select(LeadEvent)
        .where(LeadEvent.lead_id == lead_id)
        .order_by(LeadEvent.created_at.desc(), LeadEvent.id.desc())
    )
    return list(rows)


async def change_status(
    session: AsyncSession, lead: Lead, status: str, now: datetime
) -> LeadEvent | None:
    """Move the lead and log it. None when it already had that status."""
    previous = lead.status
    if not apply_status(lead, status, now):
        return None
    event = LeadEvent(
        lead_id=lead.id, kind="status", from_status=previous, to_status=status, created_at=now
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def undo_status(session: AsyncSession, lead: Lead, event_id: int, now: datetime) -> bool:
    """Take back the latest status change, as if it had not happened.

    Only the most recent change of this lead can be undone, so an old undo
    button cannot rewrite history made after it.
    """
    latest = await session.scalar(
        select(LeadEvent)
        .where(LeadEvent.lead_id == lead.id, LeadEvent.kind == "status")
        .order_by(LeadEvent.created_at.desc(), LeadEvent.id.desc())
        .limit(1)
    )
    if latest is None or latest.id != event_id or latest.to_status != lead.status:
        return False
    apply_status(lead, latest.from_status, now)
    await session.delete(latest)
    await session.commit()
    return True


async def add_note(session: AsyncSession, lead: Lead, text: str, now: datetime) -> Note | None:
    text = text.strip()
    if not text or len(text) > NOTE_MAX_LENGTH:
        return None
    note = Note(lead_id=lead.id, text=text, created_at=now)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


async def set_note_deleted(
    session: AsyncSession, lead: Lead, note_id: int, deleted_at: datetime | None
) -> Note | None:
    note = await session.get(Note, note_id)
    if note is None or note.lead_id != lead.id:
        return None
    note.deleted_at = deleted_at
    await session.commit()
    return note


async def stats_rows(session: AsyncSession) -> list[tuple[datetime, str, str]]:
    return list((await session.execute(select(Lead.created_at, Lead.status, Lead.source))).all())
