"""Seller tokens: proof that a browser created a given lead.

When the contact step saves the lead, the form receives a token. It lets the
same browser add photos, fix answers from the review step and submit, and
nothing else: it opens exactly one lead and expires after a week (the time a
seller may take to come back and finish the photos on the same phone).

Format: base64url("<lead_id>.<expires_unix>") "." base64url(HMAC-SHA256).
Stateless, so nothing is stored per token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta

TOKEN_TTL = timedelta(days=7)


class TokenInvalid(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, b"lead-token:" + payload, hashlib.sha256).digest()


def issue(key: bytes, lead_id: int, now: datetime) -> tuple[str, datetime]:
    expires = now + TOKEN_TTL
    payload = f"{lead_id}.{int(expires.timestamp())}".encode()
    return f"{_b64(payload)}.{_b64(_sign(key, payload))}", expires


def verify(key: bytes, token: str, lead_id: int, now: datetime) -> None:
    """Raise TokenInvalid unless the token opens this lead and has not expired."""
    try:
        payload_part, signature_part = token.split(".")
        payload = _unb64(payload_part)
        signature = _unb64(signature_part)
        token_lead, expires = (int(part) for part in payload.decode().split("."))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TokenInvalid("malformed token") from exc
    if not hmac.compare_digest(signature, _sign(key, payload)):
        raise TokenInvalid("bad signature")
    if token_lead != lead_id:
        raise TokenInvalid("token is for another lead")
    if now.timestamp() >= expires:
        raise TokenInvalid("token expired")
