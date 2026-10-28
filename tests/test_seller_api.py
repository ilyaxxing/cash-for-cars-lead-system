import io
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.db.models import Lead, OutboxEvent
from app.services import tokens
from app.web import seller_api
from tests.test_answers import COMPLETE

pytestmark = pytest.mark.usefixtures("clean_db")


def jpeg(width=1200, height=800, *, exif: Image.Exif | None = None) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), (40, 120, 200))
    image.save(buffer, "JPEG", exif=exif or Image.Exif())
    return buffer.getvalue()


def gps_exif(orientation: int = 1) -> Image.Exif:
    exif = Image.Exif()
    exif[0x0112] = orientation  # Orientation
    gps = exif.get_ifd(0x8825)  # GPSInfo
    gps[1] = "N"
    gps[2] = (37.0, 46.0, 30.0)
    return exif


@pytest.fixture
def client(client_for, tmp_path):
    return client_for(local_storage_dir=tmp_path / "store", secret_key="k" * 40)


async def create(client, **overrides):
    response = await client.post(
        "/api/leads", json={"answers": {**COMPLETE, **overrides}, "source": "card"}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["id"], {"Authorization": f"Bearer {body['token']}"}


async def upload(client, lead_id, auth, data, slot=None):
    files = {"file": ("photo.jpg", data, "image/jpeg")}
    form = {"slot": slot} if slot else {}
    return await client.post(f"/api/leads/{lead_id}/photos", headers=auth, files=files, data=form)


async def test_contact_step_creates_the_lead(client):
    lead_id, auth = await create(client)
    response = await client.get(f"/api/leads/{lead_id}", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["answers"]["phone"] == "+14155550142"
    assert body["answers"]["make"] == "Toyota"
    assert body["photos"] == [] and body["submitted"] is False


async def test_invalid_answers_come_back_as_codes(client):
    response = await client.post(
        "/api/leads", json={"answers": {**COMPLETE, "phone": "12", "make": ""}}
    )
    assert response.status_code == 422
    assert {(e["field"], e["code"]) for e in response.json()["errors"]} == {
        ("phone", "format"),
        ("make", "required"),
    }


async def test_earlier_year_survives_a_round_trip(client):
    lead_id, auth = await create(client, year="earlier")
    body = (await client.get(f"/api/leads/{lead_id}", headers=auth)).json()
    assert body["answers"]["year"] == "earlier"


async def test_a_lead_opens_only_with_its_own_token(client):
    first, auth = await create(client)
    second, _ = await create(client)
    assert (await client.get(f"/api/leads/{first}")).status_code == 404
    assert (await client.get(f"/api/leads/{second}", headers=auth)).status_code == 404
    bad = {"Authorization": "Bearer not.a-token"}
    assert (await client.get(f"/api/leads/{first}", headers=bad)).status_code == 404


async def test_expired_token_is_refused(client):
    lead_id, _ = await create(client)
    old, _ = tokens.issue(b"k" * 40, lead_id, datetime.now(UTC) - timedelta(days=8))
    response = await client.get(f"/api/leads/{lead_id}", headers={"Authorization": f"Bearer {old}"})
    assert response.status_code == 404


async def test_review_edit_replaces_answers(client):
    lead_id, auth = await create(client)
    edited = {**COMPLETE, "asking_price": "", "contact_method": "call", "name": "Sam Lee"}
    response = await client.patch(f"/api/leads/{lead_id}", headers=auth, json={"answers": edited})
    assert response.status_code == 200
    answers = (await client.get(f"/api/leads/{lead_id}", headers=auth)).json()["answers"]
    assert "asking_price" not in answers
    assert answers["name"] == "Sam Lee"


async def test_review_edit_is_validated(client):
    lead_id, auth = await create(client)
    response = await client.patch(
        f"/api/leads/{lead_id}", headers=auth, json={"answers": {**COMPLETE, "vin": "SHORT"}}
    )
    assert response.status_code == 422


async def test_photo_is_stored_without_location_and_upright(client, tmp_path):
    lead_id, auth = await create(client)
    # Orientation 6: the camera was turned; the stored photo must be portrait.
    response = await upload(client, lead_id, auth, jpeg(1200, 800, exif=gps_exif(6)), "front_left")
    assert response.status_code == 201, response.text
    thumb = await client.get(response.json()["thumbUrl"], headers=auth)
    assert thumb.headers["content-type"] == "image/jpeg"

    stored = [p for p in (tmp_path / "store").rglob("*.jpg") if not p.name.endswith("-thumb.jpg")]
    assert len(stored) == 1
    with Image.open(stored[0]) as image:
        assert image.width < image.height
        assert dict(image.getexif()) == {}


async def test_thumbnail_loads_with_token_in_the_query(client):
    lead_id, auth = await create(client)
    photo = (await upload(client, lead_id, auth, jpeg(), "interior")).json()
    token = auth["Authorization"].removeprefix("Bearer ")
    response = await client.get(f"{photo['thumbUrl']}?token={token}")
    assert response.status_code == 200


async def test_uploading_an_angle_again_replaces_it(client, tmp_path):
    lead_id, auth = await create(client)
    await upload(client, lead_id, auth, jpeg(), "front_left")
    await upload(client, lead_id, auth, jpeg(900, 600), "front_left")
    photos = (await client.get(f"/api/leads/{lead_id}", headers=auth)).json()["photos"]
    assert [p["slot"] for p in photos] == ["front_left"]
    assert len(list((tmp_path / "store").rglob("*.jpg"))) == 2  # one photo and its preview


async def test_photos_come_back_in_guide_order(client):
    lead_id, auth = await create(client)
    for slot in (None, "cluster", "front_left"):
        await upload(client, lead_id, auth, jpeg(), slot)
    photos = (await client.get(f"/api/leads/{lead_id}", headers=auth)).json()["photos"]
    assert [p["slot"] for p in photos] == ["front_left", "cluster", None]


@pytest.mark.parametrize(
    ("data", "slot", "code"),
    [
        (b"definitely not an image", "front_left", "format"),
        (jpeg(), "roof", "slot"),
    ],
)
async def test_bad_uploads_are_refused(client, data, slot, code):
    lead_id, auth = await create(client)
    response = await upload(client, lead_id, auth, data, slot)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == code


async def test_extra_photos_are_capped(client):
    lead_id, auth = await create(client)
    for _ in range(4):
        assert (await upload(client, lead_id, auth, jpeg())).status_code == 201
    response = await upload(client, lead_id, auth, jpeg())
    assert response.json()["errors"][0]["code"] == "limit"


async def test_deleting_the_last_photo_clears_has_photos(client, session):
    from app.db.models import Lead

    lead_id, auth = await create(client)
    photo = (await upload(client, lead_id, auth, jpeg(), "rear_left")).json()
    assert (await session.get(Lead, lead_id)).has_photos
    session.expunge_all()

    response = await client.delete(f"/api/leads/{lead_id}/photos/{photo['id']}", headers=auth)
    assert response.status_code == 204
    assert not (await session.get(Lead, lead_id)).has_photos


async def test_submit_is_final_and_idempotent(client):
    lead_id, auth = await create(client)
    first = await client.post(f"/api/leads/{lead_id}/submit", headers=auth)
    second = await client.post(f"/api/leads/{lead_id}/submit", headers=auth)
    assert first.status_code == second.status_code == 200
    assert first.json()["submittedAt"] == second.json()["submittedAt"]
    assert (await upload(client, lead_id, auth, jpeg(), "interior")).status_code == 409
    patch = await client.patch(f"/api/leads/{lead_id}", headers=auth, json={"answers": COMPLETE})
    assert patch.status_code == 409


def test_tokens_reject_tampering():
    key = b"k" * 40
    now = datetime.now(UTC)
    token, _ = tokens.issue(key, 7, now)
    tokens.verify(key, token, 7, now)
    for bad_key, bad_lead, bad_token in [
        (b"x" * 40, 7, token),
        (key, 8, token),
        (key, 7, token[:-2] + "AA"),
        (key, 7, "garbage"),
    ]:
        with pytest.raises(tokens.TokenInvalid):
            tokens.verify(bad_key, bad_token, bad_lead, now)


# --- spam protection -------------------------------------------------------------


async def test_honeypot_looks_like_success_but_stores_nothing(client, session):
    response = await client.post(
        "/api/leads", json={"answers": COMPLETE, "honeypot": "http://spam.example"}
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "token", "expiresAt"}
    assert await session.scalar(select(func.count()).select_from(Lead)) == 0
    assert await session.scalar(select(func.count()).select_from(OutboxEvent)) == 0
    # The fake token opens nothing.
    auth = {"Authorization": f"Bearer {body['token']}"}
    assert (await client.get(f"/api/leads/{body['id']}", headers=auth)).status_code == 404


async def test_one_address_cannot_flood_new_leads(client):
    for _ in range(10):
        await create(client)
    response = await client.post("/api/leads", json={"answers": COMPLETE})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "600"


async def test_requests_per_address_are_capped(client, monkeypatch):
    monkeypatch.setattr(seller_api.seller_requests, "limit", 3)
    lead_id, auth = await create(client)
    assert (await client.get(f"/api/leads/{lead_id}", headers=auth)).status_code == 200
    assert (await client.get(f"/api/leads/{lead_id}", headers=auth)).status_code == 200
    assert (await client.get(f"/api/leads/{lead_id}", headers=auth)).status_code == 429
