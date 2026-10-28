"""Adding and removing a lead's photos.

Guided angles (preset slots) hold one photo each: uploading again replaces
it. Extra photos have no slot and are capped by the preset. The objects are
written to storage before the row is committed and cleaned up if the commit
fails, so the bucket never holds photos the database does not know about
for longer than a request.
"""

from __future__ import annotations

import asyncio
import logging
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lead, Photo
from app.preset.schema import FieldSpec, Preset
from app.services.images import ImageRejected, process_upload
from app.storage import Storage

logger = logging.getLogger(__name__)


class PhotoRejected(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def photos_field(preset: Preset) -> FieldSpec:
    return next(spec for spec in preset.all_fields() if spec.type == "photos")


async def lead_photos(session: AsyncSession, lead_id: int) -> list[Photo]:
    rows = await session.scalars(select(Photo).where(Photo.lead_id == lead_id).order_by(Photo.id))
    return list(rows)


def ordered(preset: Preset, photos: list[Photo]) -> list[Photo]:
    """Guided angles in preset order first, then extras in upload order."""
    slot_order = {slot.id: index for index, slot in enumerate(photos_field(preset).slots)}
    return sorted(photos, key=lambda p: (slot_order.get(p.slot, len(slot_order)), p.id))


async def _remove_objects(storage: Storage, *keys: str) -> None:
    for key in keys:
        try:
            await storage.delete(key)
        except Exception:
            # An orphaned object costs a few kilobytes; failing the request
            # over it would cost the seller their upload.
            logger.exception("Could not delete stored object %s", key)


async def add_photo(
    session: AsyncSession,
    storage: Storage,
    preset: Preset,
    lead: Lead,
    *,
    slot: str | None,
    data: bytes,
) -> Photo:
    spec = photos_field(preset)
    if slot is not None and slot not in {s.id for s in spec.slots}:
        raise PhotoRejected("slot")

    existing = await lead_photos(session, lead.id)
    replaced = next((p for p in existing if slot is not None and p.slot == slot), None)
    if slot is None and sum(p.slot is None for p in existing) >= spec.extra:
        raise PhotoRejected("limit")

    try:
        image = await asyncio.to_thread(process_upload, data)
    except ImageRejected as exc:
        raise PhotoRejected(exc.code) from exc

    name = secrets.token_hex(16)
    key, thumb_key = f"leads/{lead.id}/{name}.jpg", f"leads/{lead.id}/{name}-thumb.jpg"
    await storage.put(key, image.full, "image/jpeg")
    await storage.put(thumb_key, image.thumb, "image/jpeg")

    photo = Photo(
        lead_id=lead.id,
        slot=slot,
        key=key,
        thumb_key=thumb_key,
        width=image.width,
        height=image.height,
        size_bytes=len(image.full),
    )
    if replaced is not None:
        await session.delete(replaced)
        await session.flush()
    session.add(photo)
    lead.has_photos = True
    try:
        await session.commit()
    except IntegrityError as exc:
        # Two uploads raced for the same angle; the other one won.
        await session.rollback()
        await _remove_objects(storage, key, thumb_key)
        raise PhotoRejected("conflict") from exc

    if replaced is not None:
        await _remove_objects(storage, replaced.key, replaced.thumb_key)
    await session.refresh(photo)
    return photo


async def delete_photo(session: AsyncSession, storage: Storage, lead: Lead, photo_id: int) -> bool:
    photo = await session.get(Photo, photo_id)
    if photo is None or photo.lead_id != lead.id:
        return False
    await session.delete(photo)
    await session.flush()
    lead.has_photos = bool(await lead_photos(session, lead.id))
    await session.commit()
    await _remove_objects(storage, photo.key, photo.thumb_key)
    return True
