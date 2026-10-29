"""Owner sign-in, sign-out and password change."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.services import auth
from app.services.leads import utcnow
from app.services.ratelimit import RateLimiter
from app.web.deps import SESSION_COOKIE, Session, SignedIn, client_ip

router = APIRouter(prefix="/api/auth")

# Ten wrong passwords per address per 15 minutes: plenty for a person who
# mistyped, far too slow for guessing.
login_attempts = RateLimiter(limit=10, window_seconds=15 * 60)


class LoginBody(BaseModel):
    password: str


class PasswordBody(BaseModel):
    # Empty when replacing the password that was handed over (auth.change_password).
    current: str = ""
    new: str


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(auth.SESSION_TTL.total_seconds()),
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


@router.post("/login")
async def login(body: LoginBody, request: Request, session: Session) -> Response:
    settings = request.app.state.settings
    ip = client_ip(request)
    if login_attempts.blocked(ip):
        return JSONResponse({"error": "too_many_attempts"}, status_code=429)
    try:
        ok = await auth.check_password(session, settings.owner_password, body.password, utcnow())
    except auth.PasswordNotConfigured:
        return JSONResponse({"error": "not_configured"}, status_code=503)
    if not ok:
        login_attempts.hit(ip)
        return JSONResponse({"error": "wrong_password"}, status_code=401)
    login_attempts.reset(ip)
    token = await auth.start_session(session, request.headers.get("user-agent"), utcnow())
    must_change = await auth.must_change_password(session)
    response = JSONResponse({"ok": True, "mustChangePassword": must_change})
    set_session_cookie(response, request, token)
    return response


@router.post("/logout")
async def logout(
    session: Session,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Response:
    if session_token:
        await auth.end_session(session, session_token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me")
async def me(owner: SignedIn, session: Session) -> dict[str, Any]:
    changed = await auth.password_changed_at(session)
    return {
        "authenticated": True,
        "mustChangePassword": await auth.must_change_password(session),
        "passwordChangedAt": changed.isoformat() if changed else None,
    }


@router.post("/password")
async def change_password(
    body: PasswordBody,
    owner: SignedIn,
    request: Request,
    session: Session,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Response:
    problem = await auth.change_password(
        session,
        request.app.state.settings.owner_password,
        current=body.current,
        new=body.new,
        keep_token=session_token or "",
        now=utcnow(),
    )
    if problem:
        return JSONResponse({"error": problem}, status_code=422)
    return JSONResponse({"ok": True})
