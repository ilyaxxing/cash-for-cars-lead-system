"""Migrations run in a database of their own, so dropping tables here cannot
disturb the shared test database other tests are using."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.session import create_engine
from tests.conftest import run_alembic

SCRATCH_DB = "carbuyout_migrations"


@pytest.fixture
async def scratch_url(database_url: str) -> AsyncIterator[str]:
    url = make_url(database_url)
    admin = create_engine(url.set(database="postgres").render_as_string(hide_password=False))
    async with admin.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB}"))
        await connection.execute(text(f"CREATE DATABASE {SCRATCH_DB}"))
    yield url.set(database=SCRATCH_DB).render_as_string(hide_password=False)
    async with admin.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB} WITH (FORCE)"))
    await admin.dispose()


def test_migrations_match_models_and_roll_back(scratch_url):
    upgrade = run_alembic("upgrade", "head", database_url=scratch_url)
    assert upgrade.returncode == 0, upgrade.stderr

    # Models and migrations describe the same schema: nothing left to generate.
    check = run_alembic("check", database_url=scratch_url)
    assert check.returncode == 0, check.stdout + check.stderr

    downgrade = run_alembic("downgrade", "base", database_url=scratch_url)
    assert downgrade.returncode == 0, downgrade.stderr
    again = run_alembic("upgrade", "head", database_url=scratch_url)
    assert again.returncode == 0, again.stderr
