"""Shared fixtures.

Database tests run against TEST_DATABASE_URL, a throwaway PostgreSQL that
tools/run_tests.sh starts and removes. Without it those tests are skipped,
so the pure-logic tests still run anywhere with plain `pytest`.
"""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.cli import new_vapid_keys
from app.config import BASE_DIR, Settings
from app.db.session import create_engine, create_session_factory
from app.preset.schema import Preset

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


def vapid_keys() -> dict[str, str]:
    """A fresh Web Push key pair, generated per test run rather than committed."""
    keys = {name.lower(): value for name, value in new_vapid_keys().items()}
    return {**keys, "vapid_subject": "mailto:owner@example.com"}


# The password an owner sets for themselves on first sign-in.
OWN_PASSWORD = "owners-own-2026"  # gitleaks:allow (test-only password)


async def sign_in(client: AsyncClient, password: str) -> None:
    """Sign in with OWNER_PASSWORD and set an own password, as the dashboard asks first."""
    assert (await client.post("/api/auth/login", json={"password": password})).status_code == 200
    response = await client.post("/api/auth/password", json={"new": OWN_PASSWORD})
    assert response.status_code == 200


def make_settings(**overrides: Any) -> Settings:
    """Settings built only from the arguments: no .env, no process environment."""
    defaults: dict[str, Any] = {
        "database_url": TEST_DATABASE_URL or "postgresql://test@localhost/test"
    }
    return Settings(_env_file=None, **{**defaults, **overrides})


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's real environment out of the tests."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture(autouse=True)
def fresh_rate_limits() -> None:
    """Rate limit counters live in memory; one test must not throttle the next."""
    from app.web import auth_api, seller_api

    auth_api.login_attempts.hits.clear()
    seller_api.new_leads.hits.clear()
    seller_api.seller_requests.hits.clear()


@pytest.fixture
def preset_data() -> dict[str, Any]:
    """The shipped US preset as plain data, for tests that tweak it."""
    raw = (BASE_DIR / "presets" / "us-car-buyout.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(raw)


@pytest.fixture
def preset(preset_data: dict[str, Any]) -> Preset:
    return Preset.model_validate(preset_data)


@pytest.fixture
def build_preset(preset_data: dict[str, Any]) -> Callable[..., Preset]:
    """Validate a modified copy of the shipped preset."""

    def build(change: Callable[[dict[str, Any]], None]) -> Preset:
        data = copy.deepcopy(preset_data)
        change(data)
        return Preset.model_validate(data)

    return build


def step_of(data: dict[str, Any], step_id: str) -> dict[str, Any]:
    return next(step for step in data["steps"] if step["id"] == step_id)


# --- database ---------------------------------------------------------------


def run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="session")
def database_url() -> str:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set (use tools/run_tests.sh)")
    result = run_alembic("upgrade", "head", database_url=TEST_DATABASE_URL)
    assert result.returncode == 0, result.stderr
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_db(engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """The shared test database, emptied after the test."""
    yield engine
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE leads, photos, notes, lead_events, owner_sessions, owner_account, "
                "push_subscriptions, notification_outbox "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
async def session(clean_db: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = create_session_factory(clean_db)
    async with factory() as session:
        yield session


# --- web --------------------------------------------------------------------


@pytest.fixture
def frontend_dist(tmp_path: Path) -> Path:
    """A stand-in for the Vite build: just the two HTML entry points."""
    page = '<html lang="en"><head><title>Page</title><!--app-config--></head><body>{}</body></html>'
    (tmp_path / "app").mkdir()
    (tmp_path / "index.html").write_text(page.format("form"), encoding="utf-8")
    (tmp_path / "app" / "index.html").write_text(page.format("dashboard"), encoding="utf-8")
    (tmp_path / "app" / "sw.js").write_text("// worker", encoding="utf-8")
    return tmp_path


@pytest.fixture
async def client_for(frontend_dist: Path) -> AsyncIterator[Callable[..., AsyncClient]]:
    """Build an app with the given settings overrides and an HTTP client for it."""
    from app.main import create_app

    apps = []

    def build(**overrides: Any) -> AsyncClient:
        settings = make_settings(**{"frontend_dist": frontend_dist, **overrides})
        app = create_app(settings)
        apps.append(app)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield build
    for app in apps:
        await app.state.engine.dispose()
