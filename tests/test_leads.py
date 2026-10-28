from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models import (
    STATUS_BOUGHT,
    STATUS_IN_WORK,
    STATUS_NEW,
    STATUS_REJECTED,
    Lead,
)
from app.services.leads import apply_status, create_lead, set_status
from tests.conftest import step_of
from tests.test_answers import COMPLETE

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


def make_lead(status=STATUS_NEW) -> Lead:
    return Lead(status=status, preset_id="us-car-buyout")


async def test_lead_is_saved_with_columns_and_answers(session, preset):
    lead = await create_lead(session, preset, COMPLETE, source="card")
    stored = await session.scalar(select(Lead).where(Lead.id == lead.id))
    assert (stored.make, stored.model, stored.phone) == ("Toyota", "Camry", "+14155550142")
    assert stored.answers["condition"] == "good"
    assert stored.status == STATUS_NEW
    assert stored.source == "card"
    assert stored.preset_id == "us-car-buyout"
    assert stored.has_photos is False
    assert stored.closed_at is None


@pytest.mark.parametrize(
    ("given", "stored"), [(None, "direct"), ("", "direct"), ("Flyer", "flyer")]
)
async def test_source_is_frozen_on_the_lead(session, preset, given, stored):
    lead = await create_lead(session, preset, COMPLETE, source=given)
    assert lead.source == stored


async def test_junk_source_falls_back_to_direct(session, preset):
    lead = await create_lead(session, preset, COMPLETE, source="<script>")
    assert lead.source == "direct"


async def test_new_preset_field_needs_no_migration(session, build_preset):
    """The point of the JSONB column: a new question is preset data only."""

    def add_question(data):
        step_of(data, "condition")["fields"].append(
            {"id": "spare_keys", "type": "yes_no", "required": True}
        )

    preset = build_preset(add_question)
    lead = await create_lead(session, preset, {**COMPLETE, "spare_keys": "yes"}, source=None)
    session.expunge_all()
    stored = await session.get(Lead, lead.id)
    assert stored.answers["spare_keys"] == "yes"


def test_closing_a_lead_starts_the_retention_clock():
    lead = make_lead(STATUS_IN_WORK)
    assert apply_status(lead, STATUS_BOUGHT, NOW)
    assert (lead.status, lead.closed_at, lead.status_changed_at) == (STATUS_BOUGHT, NOW, NOW)


def test_reopening_a_lead_stops_the_retention_clock():
    lead = make_lead(STATUS_REJECTED)
    lead.closed_at = NOW - timedelta(days=30)
    assert apply_status(lead, STATUS_IN_WORK, NOW)
    assert lead.closed_at is None


def test_moving_between_closed_statuses_restarts_the_clock():
    lead = make_lead(STATUS_BOUGHT)
    lead.closed_at = NOW - timedelta(days=30)
    apply_status(lead, STATUS_REJECTED, NOW)
    assert lead.closed_at == NOW


def test_same_status_is_not_a_change():
    lead = make_lead(STATUS_IN_WORK)
    assert not apply_status(lead, STATUS_IN_WORK, NOW)


def test_any_transition_is_allowed():
    lead = make_lead(STATUS_NEW)
    assert apply_status(lead, STATUS_BOUGHT, NOW)
    assert apply_status(lead, STATUS_NEW, NOW)
    assert lead.closed_at is None


def test_unknown_status_is_refused():
    with pytest.raises(ValueError, match="unknown status"):
        apply_status(make_lead(), "archived", NOW)


async def test_set_status_persists(session, preset):
    lead = await create_lead(session, preset, COMPLETE, source=None)
    updated = await set_status(session, lead.id, STATUS_REJECTED, now=NOW)
    assert updated.status == STATUS_REJECTED
    assert updated.closed_at == NOW
    assert await set_status(session, 999_999, STATUS_REJECTED) is None
