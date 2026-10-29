from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import sign_in
from tests.test_answers import COMPLETE
from tests.test_seller_api import jpeg, upload

pytestmark = pytest.mark.usefixtures("clean_db")

PASSWORD = "owner-pass-2026"  # gitleaks:allow (test-only password)


@pytest.fixture
async def owner(client_for, tmp_path):
    client = client_for(
        owner_password=PASSWORD,
        local_storage_dir=tmp_path / "store",
        secret_key="k" * 40,
        source_labels="flyer:Flyers",
    )
    await sign_in(client, PASSWORD)
    return client


async def new_lead(client, source="card", **answers):
    response = await client.post(
        "/api/leads", json={"answers": {**COMPLETE, **answers}, "source": source}
    )
    body = response.json()
    return body["id"], {"Authorization": f"Bearer {body['token']}"}


async def test_tabs_count_and_filter(owner):
    first, _ = await new_lead(owner)
    await new_lead(owner)
    await owner.post(f"/api/owner/leads/{first}/status", json={"status": "in_work"})

    new = (await owner.get("/api/owner/leads?tab=new")).json()
    assert new["counts"] == {"new": 1, "in_work": 1, "all": 2}
    assert len(new["leads"]) == 1
    in_work = (await owner.get("/api/owner/leads?tab=in_work")).json()
    assert [lead["id"] for lead in in_work["leads"]] == [first]


async def test_cards_carry_no_contact_details(owner):
    await new_lead(owner, email="jordan@example.com", contact_method="email")
    card = (await owner.get("/api/owner/leads?tab=all")).json()["leads"][0]
    assert card["answers"]["make"] == "Toyota"
    assert {"name", "phone", "email"}.isdisjoint(card["answers"])
    assert card["sourceLabel"] == "Business Card"


@pytest.mark.parametrize(
    ("query", "found"),
    [
        ("camry", True),
        ("toyota camry", True),
        ("jordan", True),
        ("415-555", True),
        ("(415) 555", True),
        ("4155550142", True),
        ("honda", False),
        ("camry honda", False),
    ],
)
async def test_search_by_car_seller_and_phone(owner, query, found):
    await new_lead(owner)
    leads = (await owner.get("/api/owner/leads", params={"tab": "all", "q": query})).json()["leads"]
    assert bool(leads) is found


async def test_lead_detail_has_everything_and_marks_it_seen(owner, session):
    from app.db.models import Lead

    lead_id, auth = await new_lead(owner, accident="yes", accident_details="Rear bumper scuff")
    await upload(owner, lead_id, auth, jpeg(), "front_left")
    detail = (await owner.get(f"/api/owner/leads/{lead_id}")).json()
    assert detail["answers"]["phone"] == "+14155550142"
    assert detail["answers"]["accident_details"] == "Rear bumper scuff"
    assert [p["slot"] for p in detail["photos"]] == ["front_left"]
    assert (await session.get(Lead, lead_id)).viewed_at is not None

    photo = await owner.get(detail["photos"][0]["thumbUrl"])
    assert photo.headers["content-type"] == "image/jpeg"


async def test_purged_lead_shows_no_contact_details(owner, session):
    from app.db.models import Lead

    lead_id, _ = await new_lead(owner)
    lead = await session.get(Lead, lead_id)
    lead.phone = None
    lead.name = None
    lead.purged_at = datetime.now(UTC)
    await session.commit()
    detail = (await owner.get(f"/api/owner/leads/{lead_id}")).json()
    assert detail["purgedAt"] is not None
    assert "phone" not in detail["answers"]


async def test_status_change_is_logged_and_can_be_undone(owner):
    lead_id, _ = await new_lead(owner)
    first = (
        await owner.post(f"/api/owner/leads/{lead_id}/status", json={"status": "in_work"})
    ).json()
    second = (
        await owner.post(f"/api/owner/leads/{lead_id}/status", json={"status": "bought"})
    ).json()
    detail = (await owner.get(f"/api/owner/leads/{lead_id}")).json()
    assert [(e["from"], e["to"]) for e in detail["events"]] == [
        ("in_work", "bought"),
        ("new", "in_work"),
    ]
    assert detail["closedAt"] is not None

    # Only the latest change can be taken back.
    stale = await owner.post(
        f"/api/owner/leads/{lead_id}/status", json={"status": "new", "undo": first["event"]["id"]}
    )
    assert stale.status_code == 409
    undone = await owner.post(
        f"/api/owner/leads/{lead_id}/status",
        json={"status": "in_work", "undo": second["event"]["id"]},
    )
    assert undone.json()["status"] == "in_work"
    detail = (await owner.get(f"/api/owner/leads/{lead_id}")).json()
    assert detail["status"] == "in_work" and detail["closedAt"] is None
    assert len(detail["events"]) == 1


async def test_same_status_is_not_logged(owner):
    lead_id, _ = await new_lead(owner)
    response = await owner.post(f"/api/owner/leads/{lead_id}/status", json={"status": "new"})
    assert response.json()["event"] is None


async def test_unknown_status_is_refused(owner):
    lead_id, _ = await new_lead(owner)
    response = await owner.post(f"/api/owner/leads/{lead_id}/status", json={"status": "sold"})
    assert response.status_code == 422


async def test_notes_add_delete_and_restore(owner):
    lead_id, _ = await new_lead(owner)
    note = (
        await owner.post(f"/api/owner/leads/{lead_id}/notes", json={"text": "  Viewing Thursday  "})
    ).json()
    assert note["text"] == "Viewing Thursday"
    assert (await owner.delete(f"/api/owner/leads/{lead_id}/notes/{note['id']}")).status_code == 204
    assert (await owner.get(f"/api/owner/leads/{lead_id}")).json()["notes"] == []
    await owner.post(f"/api/owner/leads/{lead_id}/notes/{note['id']}/restore")
    assert len((await owner.get(f"/api/owner/leads/{lead_id}")).json()["notes"]) == 1
    empty = await owner.post(f"/api/owner/leads/{lead_id}/notes", json={"text": "   "})
    assert empty.status_code == 422


async def test_stats_use_frozen_sources_and_custom_labels(owner):
    a, _ = await new_lead(owner, source="card")
    await new_lead(owner, source="flyer")
    await new_lead(owner, source="flyer")
    await owner.post(f"/api/owner/leads/{a}/status", json={"status": "bought"})
    stats = (await owner.get("/api/owner/stats?period=30")).json()
    assert stats["total"] == 3 and stats["purchased"] == 1
    assert [(s["source"], s["label"], s["leads"], s["purchased"]) for s in stats["sources"]] == [
        ("flyer", "Flyers", 2, 0),
        ("card", "Business Card", 1, 1),
    ]


def test_stats_periods_and_buckets():
    from zoneinfo import ZoneInfo

    from app.services.stats import Row, compute

    tz = ZoneInfo("America/New_York")
    now = datetime(2026, 10, 21, 15, 0, tzinfo=tz)  # a Wednesday
    rows = [
        Row(now - timedelta(days=1), "bought", "card"),
        Row(now - timedelta(days=2), "new", "card"),  # Monday: still this week
        Row(now - timedelta(days=3), "rejected", "direct"),  # Sunday: last week
        Row(now - timedelta(days=40), "bought", "card"),
    ]
    week = compute(rows, "7", now, tz)
    assert (week["total"], week["purchased"], week["week"]) == (3, 1, 2)
    assert [b["leads"] for b in week["buckets"]] == [0, 0, 0, 1, 1, 1, 0]

    everything = compute(rows, "all", now, tz)
    assert everything["total"] == 4 and everything["purchased"] == 2
    assert everything["buckets"][0]["start"] == "2026-09-07"  # Monday of the first lead's week
    assert sum(b["leads"] for b in everything["buckets"]) == 4
