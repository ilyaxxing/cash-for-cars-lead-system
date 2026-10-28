"""The owner's password and signed-in devices.

One owner per instance. The password starts as OWNER_PASSWORD; changing it
in the dashboard signs every other device out. Changing OWNER_PASSWORD and
restarting resets the dashboard password to it.

Sessions last a year and are extended on use: the dashboard is installed on
the owner's phone and must keep receiving leads without asking to sign in.
Only a SHA-256 of the cookie value is stored, so a database copy cannot be
used to sign in.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OwnerAccount, OwnerSession

SESSION_TTL = timedelta(days=365)
# Writing last_seen on every request would turn reads into writes.
TOUCH_INTERVAL = timedelta(hours=1)
MIN_PASSWORD_LENGTH = 8

hasher = PasswordHasher()


class PasswordNotConfigured(Exception):
    pass


def _verify(hash_: str, password: str) -> bool:
    try:
        return hasher.verify(hash_, password)
    except (VerificationError, InvalidHashError):
        return False


def _token_id(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def ensure_account(session: AsyncSession, env_password: str, now: datetime) -> OwnerAccount:
    """The owner account, created from OWNER_PASSWORD or reset when it changed."""
    if not env_password:
        raise PasswordNotConfigured
    account = await session.get(OwnerAccount, 1)
    if account is None:
        env_hash = hasher.hash(env_password)
        account = OwnerAccount(
            id=1, password_hash=env_hash, env_password_hash=env_hash, password_changed_at=now
        )
        session.add(account)
        await session.commit()
    elif not _verify(account.env_password_hash, env_password):
        # OWNER_PASSWORD was changed on purpose: it wins, and every device
        # signed in with the old password is signed out.
        env_hash = hasher.hash(env_password)
        account.password_hash = env_hash
        account.env_password_hash = env_hash
        account.password_changed_at = now
        await session.execute(delete(OwnerSession))
        await session.commit()
    return account


async def check_password(
    session: AsyncSession, env_password: str, password: str, now: datetime
) -> bool:
    account = await ensure_account(session, env_password, now)
    return _verify(account.password_hash, password)


async def start_session(session: AsyncSession, user_agent: str | None, now: datetime) -> str:
    token = secrets.token_urlsafe(32)
    session.add(
        OwnerSession(
            id=_token_id(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + SESSION_TTL,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    await session.commit()
    return token


async def resume_session(session: AsyncSession, token: str, now: datetime) -> OwnerSession | None:
    record = await session.get(OwnerSession, _token_id(token))
    if record is None:
        return None
    if record.expires_at <= now:
        await session.delete(record)
        await session.commit()
        return None
    if now - record.last_seen_at >= TOUCH_INTERVAL:
        record.last_seen_at = now
        record.expires_at = now + SESSION_TTL
        await session.commit()
    return record


async def end_session(session: AsyncSession, token: str) -> None:
    await session.execute(delete(OwnerSession).where(OwnerSession.id == _token_id(token)))
    await session.commit()


def password_problem(current: str, new: str) -> str | None:
    """Rules from the design: 8+ characters with a number, not the old one."""
    if len(new) < MIN_PASSWORD_LENGTH or not re.search(r"\d", new):
        return "weak"
    if new == current:
        return "same"
    return None


async def change_password(
    session: AsyncSession,
    env_password: str,
    *,
    current: str,
    new: str,
    keep_token: str,
    now: datetime,
) -> str | None:
    """Change the password. Returns an error code, or None on success."""
    account = await ensure_account(session, env_password, now)
    if not _verify(account.password_hash, current):
        return "wrong_current"
    problem = password_problem(current, new)
    if problem:
        return problem
    account.password_hash = hasher.hash(new)
    account.password_changed_at = now
    await session.execute(delete(OwnerSession).where(OwnerSession.id != _token_id(keep_token)))
    await session.commit()
    return None


async def password_changed_at(session: AsyncSession) -> datetime | None:
    return await session.scalar(
        select(OwnerAccount.password_changed_at).where(OwnerAccount.id == 1)
    )
