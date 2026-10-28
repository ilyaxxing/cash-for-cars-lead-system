"""Creating leads and moving them between statuses."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CLOSED_STATUSES,
    DEFAULT_SOURCE,
    EVENT_NEW_LEAD,
    EVENT_PHOTOS_ADDED,
    FIXED_ANSWER_COLUMNS,
    STATUS_NEW,
    STATUSES,
    Lead,
)
from app.notify import outbox
from app.preset.schema import Preset
from app.services.answers import EARLIER, split_answers, validate_answers
from app.services.sources import parse_source


def utcnow() -> datetime:
    return datetime.now(UTC)


async def create_lead(
    session: AsyncSession,
    preset: Preset,
    raw_answers: Mapping[str, Any],
    *,
    source: str | None,
) -> Lead:
    """Validate the answers up to the submit step and save a new lead.

    Called only when the contact step is submitted, so an abandoned form
    leaves nothing behind in the database.
    """
    values = validate_answers(preset, raw_answers)
    columns, answers = split_answers(preset, values)
    lead = Lead(
        **columns,
        answers=answers,
        preset_id=preset.id,
        # Frozen here: the seller may have scanned the card days ago.
        source=parse_source(source) or DEFAULT_SOURCE,
        status=STATUS_NEW,
    )
    session.add(lead)
    await session.flush()
    # The owner hears about the lead right away, photos or not.
    outbox.enqueue(session, lead.id, EVENT_NEW_LEAD)
    await session.commit()
    await session.refresh(lead)
    return lead


def apply_status(lead: Lead, status: str, now: datetime) -> bool:
    """Move the lead to a status. Returns False when nothing changed.

    Any transition is allowed, including reopening a closed lead. closed_at
    follows the status: set on entering a closed status, cleared on leaving
    it, because the retention period counts from the moment the deal ended,
    not from when the lead arrived.
    """
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    if lead.status == status:
        return False
    lead.status = status
    lead.status_changed_at = now
    lead.closed_at = now if status in CLOSED_STATUSES else None
    return True


async def set_status(
    session: AsyncSession, lead_id: int, status: str, *, now: datetime | None = None
) -> Lead | None:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        return None
    if apply_status(lead, status, now or utcnow()):
        await session.commit()
        await session.refresh(lead)
    return lead


async def update_answers(
    session: AsyncSession, preset: Preset, lead: Lead, raw_answers: Mapping[str, Any]
) -> Lead:
    """Replace the answers after an edit on the review step.

    The full set is validated again, exactly as on creation: an edit can
    remove an answer (a skipped price) as well as change one.
    """
    values = validate_answers(preset, raw_answers)
    columns, answers = split_answers(preset, values)
    for name, value in columns.items():
        setattr(lead, name, value)
    lead.answers = answers
    await session.commit()
    await session.refresh(lead)
    return lead


def form_values(preset: Preset, lead: Lead) -> dict[str, Any]:
    """The lead's answers keyed by preset field id, as the form sent them.

    Used to restore an unfinished form on the seller's phone.
    """
    values: dict[str, Any] = {}
    for spec in preset.all_fields():
        if spec.type == "photos":
            continue
        if spec.id in FIXED_ANSWER_COLUMNS:
            value = getattr(lead, spec.id)
        else:
            value = lead.answers.get(spec.id)
        if value is None and f"{spec.id}_before" in lead.answers:
            value = EARLIER
        if value is not None:
            values[spec.id] = value
    return values


async def submit(session: AsyncSession, lead: Lead, *, now: datetime | None = None) -> bool:
    """Final submit from the review step. Returns False if it was already submitted."""
    if lead.submitted_at is not None:
        return False
    lead.submitted_at = now or utcnow()
    if lead.has_photos:
        # The first notification said "no photos yet"; now they are here.
        outbox.enqueue(session, lead.id, EVENT_PHOTOS_ADDED)
    await session.commit()
    await session.refresh(lead)
    return True
