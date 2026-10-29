"""Request dependencies shared by the API routers."""

from __future__ import annotations

import contextlib
import ipaddress
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OwnerSession
from app.services import auth
from app.services.leads import utcnow

SESSION_COOKIE = "session"


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]


def client_ip(request: Request) -> str:
    """The visitor's address, for the in-memory rate limits only; never stored.

    Behind Railway it comes from X-Real-IP (CLIENT_IP_HEADER, set by
    tools/deploy.py). Checked live on 2026-10-20: Railway's edge replaces both
    X-Real-IP and X-Forwarded-For with the real address whatever the client
    sends, but only X-Real-IP is documented. client.host is avoided on purpose:
    uvicorn started with --forwarded-allow-ips='*' takes the first
    X-Forwarded-For entry, so behind a proxy that passes a client's own value
    through, a script could claim a new address on every request and never
    reach a limit.
    """
    header = request.app.state.settings.client_ip_header
    if header:
        value = request.headers.get(header, "").strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


async def signed_in_session(
    request: Request,
    session: Session,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> OwnerSession:
    """A signed-in device, whatever its password; for sign-in and password change."""
    if not request.app.state.owner_checked:
        # Once per start: a new OWNER_PASSWORD resets the dashboard password
        # and signs every device out right away, not at the next sign-in.
        with contextlib.suppress(auth.PasswordNotConfigured):
            await auth.ensure_account(session, request.app.state.settings.owner_password, utcnow())
        request.app.state.owner_checked = True
    if not session_token:
        raise HTTPException(status_code=401)
    record = await auth.resume_session(session, session_token, utcnow())
    if record is None:
        raise HTTPException(status_code=401)
    return record


SignedIn = Annotated[OwnerSession, Depends(signed_in_session)]


async def owner_session(record: SignedIn, session: Session) -> OwnerSession:
    """A signed-in owner who has replaced the password that was handed over."""
    if await auth.must_change_password(session):
        raise HTTPException(status_code=403, detail="password_change_required")
    return record


Owner = Annotated[OwnerSession, Depends(owner_session)]
