"""API behind the owner dashboard. Every route needs a signed-in session."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.db.models import STATUSES, Lead, LeadEvent, Note, Photo
from app.preset.schema import Preset
from app.services import dashboard
from app.services import leads as lead_service
from app.services import stats as stats_service
from app.services.answers import personal_fields
from app.services.photos import ordered
from app.services.sources import source_label
from app.storage import StorageError
from app.web.deps import Owner, Session

router = APIRouter(prefix="/api/owner")

CARD_PHOTOS = 1


class StatusBody(BaseModel):
    status: str
    undo: int | None = None


class NoteBody(BaseModel):
    text: str


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def photo_json(photo: Photo) -> dict[str, Any]:
    base = f"/api/owner/photos/{photo.id}"
    return {"id": photo.id, "slot": photo.slot, "thumbUrl": f"{base}/thumb", "url": f"{base}/full"}


def event_json(event: LeadEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "kind": event.kind,
        "from": event.from_status,
        "to": event.to_status,
        "createdAt": iso(event.created_at),
    }


def note_json(note: Note) -> dict[str, Any]:
    return {"id": note.id, "text": note.text, "createdAt": iso(note.created_at)}


def label_for(request: Request, source: str) -> str:
    settings = request.app.state.settings
    return source_label(source, settings.source_labels, request.app.state.messages)


def answers_for(preset: Preset, lead: Lead, *, personal: bool) -> dict[str, Any]:
    values = lead_service.form_values(preset, lead)
    if not personal:
        for field_id in personal_fields(preset):
            values.pop(field_id, None)
    return values


def card_json(request: Request, lead: Lead, photos: list[Photo]) -> dict[str, Any]:
    preset = request.app.state.preset
    shown = ordered(preset, photos)
    return {
        "id": lead.id,
        "status": lead.status,
        "createdAt": iso(lead.created_at),
        "source": lead.source,
        "sourceLabel": label_for(request, lead.source),
        "answers": answers_for(preset, lead, personal=False),
        "photoCount": len(shown),
        "photos": [photo_json(p) for p in shown[:CARD_PHOTOS]],
    }


async def owned_lead(session: Session, lead_id: int) -> Lead:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404)
    return lead


@router.get("/leads")
async def list_leads(
    owner: Owner,
    request: Request,
    session: Session,
    tab: Literal["new", "in_work", "all"] = "new",
    q: str = "",
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    leads, more = await dashboard.list_leads(session, tab, q.strip(), offset)
    photos = await dashboard.photos_by_lead(session, [lead.id for lead in leads])
    return {
        "counts": await dashboard.tab_counts(session),
        "leads": [card_json(request, lead, photos[lead.id]) for lead in leads],
        "hasMore": more,
    }


@router.get("/leads/{lead_id}")
async def read_lead(
    lead_id: int, owner: Owner, request: Request, session: Session
) -> dict[str, Any]:
    lead = await owned_lead(session, lead_id)
    if lead.viewed_at is None:
        # The first time the owner opens it; kept for a future "unseen" mark.
        lead.viewed_at = lead_service.utcnow()
        await session.commit()
    preset = request.app.state.preset
    photos = (await dashboard.photos_by_lead(session, [lead.id]))[lead.id]
    return {
        **card_json(request, lead, photos),
        "answers": answers_for(preset, lead, personal=lead.purged_at is None),
        "photos": [photo_json(p) for p in ordered(preset, photos)],
        "submittedAt": iso(lead.submitted_at),
        "closedAt": iso(lead.closed_at),
        "statusChangedAt": iso(lead.status_changed_at),
        "purgedAt": iso(lead.purged_at),
        "hasPhotos": lead.has_photos,
        "notes": [note_json(n) for n in await dashboard.notes_for(session, lead.id)],
        "events": [event_json(e) for e in await dashboard.events_for(session, lead.id)],
    }


@router.post("/leads/{lead_id}/status")
async def set_status(lead_id: int, body: StatusBody, owner: Owner, session: Session) -> Response:
    if body.status not in STATUSES:
        raise HTTPException(status_code=422, detail="unknown status")
    lead = await owned_lead(session, lead_id)
    now = lead_service.utcnow()
    if body.undo is not None:
        if not await dashboard.undo_status(session, lead, body.undo, now):
            raise HTTPException(status_code=409, detail="nothing to undo")
        return JSONResponse({"status": lead.status, "event": None})
    event = await dashboard.change_status(session, lead, body.status, now)
    return JSONResponse({"status": lead.status, "event": event_json(event) if event else None})


@router.post("/leads/{lead_id}/notes", status_code=201)
async def add_note(lead_id: int, body: NoteBody, owner: Owner, session: Session) -> Response:
    lead = await owned_lead(session, lead_id)
    note = await dashboard.add_note(session, lead, body.text, lead_service.utcnow())
    if note is None:
        raise HTTPException(status_code=422, detail="empty or too long")
    return JSONResponse(note_json(note), status_code=201)


@router.delete("/leads/{lead_id}/notes/{note_id}", status_code=204)
async def delete_note(lead_id: int, note_id: int, owner: Owner, session: Session) -> Response:
    lead = await owned_lead(session, lead_id)
    if not await dashboard.set_note_deleted(session, lead, note_id, lead_service.utcnow()):
        raise HTTPException(status_code=404)
    return Response(status_code=204)


@router.post("/leads/{lead_id}/notes/{note_id}/restore")
async def restore_note(
    lead_id: int, note_id: int, owner: Owner, session: Session
) -> dict[str, Any]:
    lead = await owned_lead(session, lead_id)
    note = await dashboard.set_note_deleted(session, lead, note_id, None)
    if note is None:
        raise HTTPException(status_code=404)
    return note_json(note)


@router.get("/photos/{photo_id}/{size}")
async def photo_file(
    photo_id: int, size: Literal["thumb", "full"], owner: Owner, request: Request, session: Session
) -> Response:
    photo = await session.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404)
    try:
        data = await request.app.state.storage.get(
            photo.thumb_key if size == "thumb" else photo.key
        )
    except StorageError:
        raise HTTPException(status_code=404) from None
    # Private: the browser may keep it, shared caches may not.
    return Response(
        data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"}
    )


@router.get("/stats")
async def stats(
    owner: Owner,
    request: Request,
    session: Session,
    period: Literal["7", "30", "all"] = "30",
) -> dict[str, Any]:
    rows = [stats_service.Row(*row) for row in await dashboard.stats_rows(session)]
    settings = request.app.state.settings
    result = stats_service.compute(rows, period, lead_service.utcnow(), settings.tz)
    for source in result["sources"]:
        source["label"] = label_for(request, source["source"])
    return result
