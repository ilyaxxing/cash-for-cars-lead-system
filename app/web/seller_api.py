"""API used by the seller form.

The lead is created when the contact step is submitted; from then on the
form holds a token that opens this one lead (see app/services/tokens.py).
Errors carry codes, not wording: the form looks the text up in the locale.

Spam protection: a honeypot field on the contact step and per-address rate
limits. Addresses are counted in memory only and never stored or logged.
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.db.models import Lead
from app.services import leads as lead_service
from app.services import photos as photo_service
from app.services import tokens
from app.services.answers import AnswersInvalid
from app.services.images import MAX_UPLOAD_BYTES
from app.services.ratelimit import RateLimiter
from app.storage import StorageError
from app.web.deps import Session, client_ip

logger = logging.getLogger(__name__)

# Generous on purpose: a mobile carrier puts many phones behind one address,
# and a car lot's Wi-Fi can send several sellers in an hour. The limits only
# have to stop a script, not a busy Saturday.
new_leads = RateLimiter(limit=10, window_seconds=60 * 60)
seller_requests = RateLimiter(limit=600, window_seconds=60 * 60)


def rate_limited() -> HTTPException:
    return HTTPException(status_code=429, headers={"Retry-After": "600"})


async def limit_requests(request: Request) -> None:
    if not seller_requests.hit(client_ip(request)):
        raise rate_limited()


router = APIRouter(prefix="/api/leads", dependencies=[Depends(limit_requests)])


class CreateLeadBody(BaseModel):
    answers: dict[str, Any]
    source: str | None = None
    # Honeypot: a field people never see, so only a bot fills it in.
    honeypot: str | None = None


class UpdateLeadBody(BaseModel):
    answers: dict[str, Any]


def error_response(status: int, errors: list[dict[str, Any]]) -> JSONResponse:
    return JSONResponse({"errors": errors}, status_code=status)


def invalid_answers(exc: AnswersInvalid) -> JSONResponse:
    return error_response(
        422, [{"field": e.field, "code": e.code, "params": e.params} for e in exc.errors]
    )


async def seller_lead(
    lead_id: int,
    request: Request,
    session: Session,
    authorization: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
) -> Lead:
    """The lead the request's token opens, or 404.

    Wrong lead, bad signature and expiry all look the same from outside, so
    the response cannot be used to probe which leads exist.
    """
    raw = token
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    try:
        if not raw:
            raise tokens.TokenInvalid("no token")
        tokens.verify(request.app.state.settings.signing_key, raw, lead_id, lead_service.utcnow())
    except tokens.TokenInvalid:
        raise HTTPException(status_code=404) from None
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404)
    return lead


SellerLead = Annotated[Lead, Depends(seller_lead)]


def thumb_url(lead_id: int, photo_id: int) -> str:
    return f"/api/leads/{lead_id}/photos/{photo_id}/thumb"


def editable(lead: Lead) -> None:
    if lead.submitted_at is not None:
        raise HTTPException(status_code=409, detail="already submitted")


@router.post("", status_code=201)
async def create_lead(body: CreateLeadBody, request: Request, session: Session) -> Response:
    if not new_leads.hit(client_ip(request)):
        raise rate_limited()
    if body.honeypot:
        # Looks like success, so the bot has nothing to learn; nothing is
        # stored and nobody is notified. The token opens nothing.
        logger.info("Honeypot filled in: inquiry dropped")
        expires = lead_service.utcnow() + tokens.TOKEN_TTL
        fake = {
            "id": secrets.randbelow(9000) + 1000,
            "token": secrets.token_urlsafe(32),
            "expiresAt": expires.isoformat(),
        }
        return JSONResponse(fake, status_code=201)
    preset = request.app.state.preset
    try:
        lead = await lead_service.create_lead(session, preset, body.answers, source=body.source)
    except AnswersInvalid as exc:
        return invalid_answers(exc)
    request.app.state.wake_outbox()
    token, expires = tokens.issue(
        request.app.state.settings.signing_key, lead.id, lead_service.utcnow()
    )
    return JSONResponse(
        {"id": lead.id, "token": token, "expiresAt": expires.isoformat()}, status_code=201
    )


@router.get("/{lead_id}")
async def read_lead(lead: SellerLead, request: Request, session: Session) -> dict[str, Any]:
    preset = request.app.state.preset
    photos = photo_service.ordered(preset, await photo_service.lead_photos(session, lead.id))
    return {
        "id": lead.id,
        "answers": lead_service.form_values(preset, lead),
        "photos": [
            {"id": p.id, "slot": p.slot, "thumbUrl": thumb_url(lead.id, p.id)} for p in photos
        ],
        "submitted": lead.submitted_at is not None,
    }


@router.patch("/{lead_id}")
async def update_lead(
    body: UpdateLeadBody, lead: SellerLead, request: Request, session: Session
) -> Response:
    editable(lead)
    try:
        await lead_service.update_answers(session, request.app.state.preset, lead, body.answers)
    except AnswersInvalid as exc:
        return invalid_answers(exc)
    return JSONResponse({"id": lead.id})


@router.post("/{lead_id}/photos", status_code=201)
async def upload_photo(
    lead: SellerLead,
    request: Request,
    session: Session,
    file: Annotated[UploadFile, File()],
    slot: Annotated[str | None, Form()] = None,
) -> Response:
    editable(lead)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        photo = await photo_service.add_photo(
            session,
            request.app.state.storage,
            request.app.state.preset,
            lead,
            slot=slot or None,
            data=data,
        )
    except photo_service.PhotoRejected as exc:
        return error_response(422, [{"field": "photos", "code": exc.code, "params": {}}])
    return JSONResponse(
        {"id": photo.id, "slot": photo.slot, "thumbUrl": thumb_url(lead.id, photo.id)},
        status_code=201,
    )


@router.delete("/{lead_id}/photos/{photo_id}", status_code=204)
async def remove_photo(
    photo_id: int, lead: SellerLead, request: Request, session: Session
) -> Response:
    editable(lead)
    if not await photo_service.delete_photo(session, request.app.state.storage, lead, photo_id):
        raise HTTPException(status_code=404)
    return Response(status_code=204)


@router.get("/{lead_id}/photos/{photo_id}/thumb")
async def photo_thumb(
    photo_id: int, lead: SellerLead, request: Request, session: Session
) -> Response:
    photos = await photo_service.lead_photos(session, lead.id)
    photo = next((p for p in photos if p.id == photo_id), None)
    if photo is None:
        raise HTTPException(status_code=404)
    try:
        data = await request.app.state.storage.get(photo.thumb_key)
    except StorageError:
        raise HTTPException(status_code=404) from None
    return Response(
        data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"}
    )


@router.post("/{lead_id}/submit")
async def submit_lead(lead: SellerLead, request: Request, session: Session) -> dict[str, Any]:
    if await lead_service.submit(session, lead):
        request.app.state.wake_outbox()
    return {"id": lead.id, "submittedAt": lead.submitted_at.isoformat()}
