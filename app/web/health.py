"""Health check that a deploy can wait on.

"The container is running" proves nothing: the app in it can fail at
startup (a bad setting, a migration that did not apply) and answer nobody,
and nothing says so unless someone checks. The deploy script waits until
this endpoint reports the commit it just shipped and the latest migration,
and only then calls the deploy done.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache
def expected_revision() -> str | None:
    return ScriptDirectory.from_config(Config(BASE_DIR / "alembic.ini")).get_current_head()


@router.get("/healthz", include_in_schema=False)
async def healthz(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    try:
        async with request.app.state.session_factory() as session:
            revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:
        logger.exception("Health check could not reach the database")
        return JSONResponse({"status": "error", "reason": "database"}, status_code=503)

    body = {"version": settings.version, "revision": revision}
    if revision != expected_revision():
        return JSONResponse({"status": "error", "reason": "migrations", **body}, status_code=503)
    return JSONResponse({"status": "ok", **body})
