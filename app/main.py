"""Application factory.

Run with: uvicorn --factory app.main:create_app

Everything that can be wrong with the configuration (settings, preset,
locale) is checked here, before the server accepts a single request.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.branding import Brand
from app.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory
from app.i18n import load_messages
from app.notify import outbox
from app.notify.registry import create_channels
from app.preset.loader import check_texts, load_preset
from app.services import retention
from app.storage import create_storage
from app.web import auth_api, brand, health, owner_api, pages, privacy, push_api, seller_api
from app.web.privacy import check_policy
from app.web.security import same_origin_only


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    if settings.is_production and not settings.client_ip_header:
        logging.getLogger(__name__).warning(
            "CLIENT_IP_HEADER is empty: rate limits key on the connecting address, "
            "which behind a proxy may be one the client chose"
        )

    preset = load_preset(settings.presets_dir, settings.preset, settings.preset_file)
    messages = load_messages(settings.locales_dir, settings.locale, settings.locale_file)
    check_texts(preset, messages)
    check_policy(settings)
    # The client's logo, icon and photo files: a broken one stops the start too.
    looks = Brand.load(settings)

    engine = create_engine(settings.database_url)

    session_factory = create_session_factory(engine)
    storage = create_storage(settings)
    channels = create_channels(settings, session_factory)
    outbox_wakeup = asyncio.Event()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Background jobs. One replica only: two copies would run them twice.
        workers = [
            asyncio.create_task(
                outbox.run(
                    session_factory,
                    channels,
                    messages,
                    settings,
                    preset.phone_region,
                    outbox_wakeup,
                )
            ),
            asyncio.create_task(retention.run(session_factory, preset, storage)),
        ]
        # Draw the home-screen icons now rather than on the first request.
        await asyncio.to_thread(lambda: looks.icons)
        yield
        for worker in workers:
            worker.cancel()
        for worker in workers:
            with suppress(asyncio.CancelledError):
                await worker
        await engine.dispose()

    # No interactive API docs: the API is internal to this app's own pages.
    app = FastAPI(
        title=settings.brand_name,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.middleware("http")(same_origin_only)
    app.state.settings = settings
    app.state.engine = engine
    app.state.preset = preset
    app.state.messages = messages
    app.state.brand = looks
    app.state.session_factory = session_factory
    app.state.channels = channels
    app.state.wake_outbox = outbox_wakeup.set
    app.state.storage = storage

    app.include_router(health.router)
    app.include_router(seller_api.router)
    app.include_router(auth_api.router)
    app.include_router(owner_api.router)
    app.include_router(push_api.router)
    app.include_router(privacy.router)
    # Icons and brand files come before the pages router, whose /app/{path}
    # catch-all would answer for them otherwise.
    app.include_router(brand.router)
    # Static files from the Vite build. check_dir=False lets the API and the
    # tests run without a frontend build.
    app.mount(
        "/assets",
        StaticFiles(directory=settings.frontend_dist / "assets", check_dir=False),
        name="assets",
    )
    app.include_router(pages.router)
    return app
