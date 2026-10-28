import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db.models import Lead, Photo
from app.db.session import create_session_factory
from app.services import retention
from app.services.leads import create_lead, set_status
from app.storage import LocalStorage
from tests.test_answers import COMPLETE

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "uploads")


async def closed_lead(session, preset, storage, *, days_ago, status="rejected", photos=2):
    lead = await create_lead(
        session, preset, {**COMPLETE, "email": "jordan@example.com"}, source=None
    )
    await set_status(session, lead.id, status, now=NOW - timedelta(days=days_ago))
    for n in range(photos):
        key, thumb = f"leads/{lead.id}/{n}.webp", f"leads/{lead.id}/{n}-thumb.webp"
        await storage.put(key, b"photo", "image/webp")
        await storage.put(thumb, b"thumb", "image/webp")
        session.add(
            Photo(lead_id=lead.id, key=key, thumb_key=thumb, width=1, height=1, size_bytes=5)
        )
    await session.commit()
    return lead.id


async def purge(clean_db, preset, storage, now=NOW):
    return await retention.purge_expired(create_session_factory(clean_db), preset, storage, now)


async def reload(session, lead_id) -> Lead:
    session.expunge_all()
    return await session.get(Lead, lead_id)


async def test_personal_data_and_photos_go_after_the_period(session, preset, storage, clean_db):
    lead_id = await closed_lead(session, preset, storage, days_ago=91)
    result = await purge(clean_db, preset, storage)
    assert (result.leads, result.photos, result.retry) == (1, 2, 0)

    lead = await reload(session, lead_id)
    assert (lead.name, lead.phone) == (None, None)
    assert "email" not in lead.answers
    assert lead.purged_at == NOW
    # The car and the outcome stay for statistics.
    assert (lead.make, lead.model, lead.year, lead.mileage) == ("Toyota", "Camry", 2019, 78400)
    assert lead.status == "rejected" and lead.answers["condition"] == "good"
    assert await session.scalar(select(func.count()).select_from(Photo)) == 0
    assert not any(path.is_file() for path in storage.root.rglob("*"))


async def test_the_period_counts_from_closing(session, preset, storage, clean_db):
    recent = await closed_lead(session, preset, storage, days_ago=89, status="bought")
    open_lead = await create_lead(session, preset, COMPLETE, source=None)
    open_lead.created_at = NOW - timedelta(days=400)
    await session.commit()

    assert (await purge(clean_db, preset, storage)).leads == 0
    assert (await reload(session, recent)).phone == "+14155550142"
    assert (await reload(session, open_lead.id)).name == "Jordan Lee"


async def test_a_purged_lead_is_not_processed_again(session, preset, storage, clean_db):
    await closed_lead(session, preset, storage, days_ago=120, photos=0)
    assert (await purge(clean_db, preset, storage)).leads == 1
    assert (await purge(clean_db, preset, storage, NOW + timedelta(days=1))).leads == 0


class FlakyStorage(LocalStorage):
    def __init__(self, root, failing):
        super().__init__(root)
        self.failing = failing

    async def delete(self, key):
        if key in self.failing:
            raise OSError("bucket unavailable")
        await super().delete(key)


async def test_photos_that_could_not_be_deleted_are_retried(session, preset, storage, clean_db):
    lead_id = await closed_lead(session, preset, storage, days_ago=95)
    flaky = FlakyStorage(storage.root, failing={f"leads/{lead_id}/1.webp"})

    result = await purge(clean_db, preset, flaky)
    assert (result.leads, result.photos, result.retry) == (0, 1, 1)
    lead = await reload(session, lead_id)
    # Name and phone are gone at once; only the lead's mark waits for its photos.
    assert (lead.phone, lead.purged_at) == (None, None)

    result = await purge(clean_db, preset, storage, NOW + timedelta(days=1))
    assert (result.leads, result.photos, result.retry) == (1, 1, 0)
    assert await session.scalar(select(func.count()).select_from(Photo)) == 0


async def test_the_daily_pass_logs_and_survives_errors(monkeypatch, caplog):
    outcomes = [RuntimeError("database down"), retention.PassResult()]

    async def fake_purge(*args):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def fake_sleep(seconds):
        assert seconds == 86400
        if not outcomes:
            raise asyncio.CancelledError

    monkeypatch.setattr(retention, "purge_expired", fake_purge)
    monkeypatch.setattr(retention.asyncio, "sleep", fake_sleep)
    with (
        caplog.at_level(logging.INFO, logger="app.services.retention"),
        pytest.raises(asyncio.CancelledError),
    ):
        await retention.run(None, None, None)

    lines = [(r.levelname, r.getMessage()) for r in caplog.records]
    assert lines[0][1].startswith("Retention: personal data is erased 90 days")
    assert lines[1][0] == "ERROR" and "failed" in lines[1][1]
    assert lines[2] == ("INFO", "Retention pass: nothing to erase")


def test_the_period_is_ninety_days():
    assert retention.RETENTION_DAYS == 90
