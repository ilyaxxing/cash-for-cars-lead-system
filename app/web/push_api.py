"""Push notification settings for the owner's devices."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.db.models import PushSubscription
from app.notify import test_notification
from app.notify.push import PushChannel, allowed_endpoint
from app.services.leads import utcnow
from app.web.deps import Owner, Session

router = APIRouter(prefix="/api/owner/push")


class Keys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionBody(BaseModel):
    endpoint: str
    keys: Keys


class EndpointBody(BaseModel):
    endpoint: str | None = None


def healthy(subscription: PushSubscription) -> bool:
    if not subscription.failure_count:
        return True
    return bool(
        subscription.last_success_at
        and subscription.last_failure_at
        and subscription.last_success_at >= subscription.last_failure_at
    )


@router.get("")
async def status(owner: Owner, request: Request, session: Session) -> dict[str, Any]:
    """What the Settings screen and the "notifications are not reaching you" warning need."""
    settings = request.app.state.settings
    devices = list(await session.scalars(select(PushSubscription)))
    successes = [d.last_success_at for d in devices if d.last_success_at]
    working = [d for d in devices if healthy(d)]
    return {
        "configured": settings.push_configured,
        "publicKey": settings.vapid_public_key,
        "devices": len(devices),
        "workingDevices": len(working),
        "lastSuccessAt": max(successes).isoformat() if successes else None,
        "problem": settings.push_configured and not working,
    }


@router.post("/subscriptions", status_code=201)
async def subscribe(
    body: SubscriptionBody, owner: Owner, request: Request, session: Session
) -> Response:
    if not allowed_endpoint(body.endpoint):
        return JSONResponse({"error": "unknown_push_service"}, status_code=422)
    existing = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    if existing is None:
        existing = PushSubscription(endpoint=body.endpoint, p256dh="", auth="")
        session.add(existing)
    existing.p256dh = body.keys.p256dh
    existing.auth = body.keys.auth
    existing.user_agent = (request.headers.get("user-agent") or "")[:255] or None
    existing.failure_count = 0
    await session.commit()
    return JSONResponse({"ok": True}, status_code=201)


@router.post("/unsubscribe")
async def unsubscribe(body: EndpointBody, owner: Owner, session: Session) -> dict[str, bool]:
    if body.endpoint:
        await session.execute(
            delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
        )
        await session.commit()
    return {"ok": True}


@router.post("/test")
async def send_test(body: EndpointBody, owner: Owner, request: Request) -> Response:
    """Send the test notification to this device (or every device) right now."""
    state = request.app.state
    if not state.settings.push_configured:
        raise HTTPException(status_code=503, detail="push is not configured")
    channel = PushChannel(state.settings, state.session_factory)
    result = await channel.send(test_notification(state.messages, state.settings), body.endpoint)
    if result.nobody:
        return JSONResponse({"error": "not_subscribed"}, status_code=409)
    return JSONResponse(
        {"delivered": result.delivered, "failed": result.failed, "at": utcnow().isoformat()}
    )
