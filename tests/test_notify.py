import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from pywebpush import WebPushException
from sqlalchemy import select

from app.config import BASE_DIR
from app.db.models import Lead, OutboxEvent, PushSubscription
from app.i18n import format_money, load_messages
from app.notify import Delivery, build, outbox
from app.notify import push as push_module
from app.notify.push import PushChannel, allowed_endpoint
from app.notify.registry import UnknownChannel, create_channels
from app.services.leads import create_lead, submit
from tests.conftest import make_settings, sign_in, vapid_keys
from tests.test_answers import COMPLETE

MESSAGES = load_messages(BASE_DIR / "locales", "en")
FCM = "https://fcm.googleapis.com/fcm/send/abc123"
SUBSCRIPTION = {"endpoint": FCM, "keys": {"p256dh": "BPkey", "auth": "authsecret"}}
PASSWORD = "owner-pass-2026"  # gitleaks:allow (test-only password)


KEYS = vapid_keys()


def lead(**overrides) -> Lead:
    values = dict(id=7, make="Toyota", model="Camry", year=2019, asking_price=21500)
    values.update(overrides)
    return Lead(
        **values, name="Jordan Lee", phone="+14155550142", answers={"email": "j@example.com"}
    )


# --- what a notification says ------------------------------------------------


def test_new_lead_notification_has_car_and_price_only():
    note = build("new_lead", lead(), 0, MESSAGES, make_settings())
    assert note.title == "New lead: 2019 Toyota Camry"
    assert note.body == "$21,500 · No photos yet"
    assert note.url == "/app/leads/7"
    text = json.dumps(note.__dict__)
    for personal in ("Jordan", "Lee", "4155550142", "example.com"):
        assert personal not in text


def test_photos_added_and_missing_price():
    note = build("photos_added", lead(asking_price=None), 6, MESSAGES, make_settings())
    assert note.title == "Photos added: 2019 Toyota Camry"
    assert note.body == "6 photos · No price given"


def test_price_is_written_the_way_the_country_writes_it():
    settings = make_settings(currency="RUB", locale="ru")
    note = build("new_lead", lead(asking_price=850000), 0, MESSAGES, settings, "RU")
    assert note.body.startswith("850\N{NO-BREAK SPACE}000\N{NO-BREAK SPACE}₽ ·")


@pytest.mark.parametrize(
    ("locale", "region", "currency", "written"),
    [
        ("en", "US", "USD", "$21,500"),
        ("en", "CA", "CAD", "$21,500"),
        ("de", "DE", "EUR", "21.500\N{NO-BREAK SPACE}€"),
        # No such pair in the locale data: the language's own way.
        ("en", "RU", "USD", "$21,500"),
        ("zh-Hant", "TW", "TWD", "$21,500"),
        ("tr", "TR", "TRY", "₺21.500"),
    ],
)
def test_money_matches_the_browser(locale, region, currency, written):
    assert format_money(21500, currency, locale, region) == written


# --- the outbox ----------------------------------------------------------------


async def test_saving_a_lead_queues_its_notification(session, preset):
    created = await create_lead(session, preset, COMPLETE, source=None)
    events = list(await session.scalars(select(OutboxEvent)))
    assert [(e.lead_id, e.kind, e.status) for e in events] == [(created.id, "new_lead", "pending")]


async def test_final_submit_with_photos_queues_a_second_notification(session, preset):
    created = await create_lead(session, preset, COMPLETE, source=None)
    created.has_photos = True
    await submit(session, created)
    kinds = [e.kind for e in await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id))]
    assert kinds == ["new_lead", "photos_added"]


async def test_final_submit_without_photos_stays_quiet(session, preset):
    created = await create_lead(session, preset, COMPLETE, source=None)
    await submit(session, created)
    assert len(list(await session.scalars(select(OutboxEvent)))) == 1


class FakeChannel:
    name = "fake"

    def __init__(self, *results: Delivery):
        self.results = list(results)
        self.sent = []

    async def send(self, notification):
        self.sent.append(notification)
        return self.results.pop(0) if self.results else Delivery(delivered=1)


async def run_once(engine, channel, now):
    from app.db.session import create_session_factory

    return await outbox.process_due(
        create_session_factory(engine), [channel], MESSAGES, make_settings(), now
    )


async def test_delivered_event_is_marked_sent(session, preset, clean_db):
    await create_lead(session, preset, COMPLETE, source=None)
    channel = FakeChannel(Delivery(delivered=1))
    now = datetime.now(UTC)
    assert await run_once(clean_db, channel, now) == 1
    session.expunge_all()
    event = await session.scalar(select(OutboxEvent))
    assert (event.status, event.attempts) == ("sent", 1)
    assert channel.sent[0].title == "New lead: 2019 Toyota Camry"


async def test_failures_are_retried_then_given_up(session, preset, clean_db):
    await create_lead(session, preset, COMPLETE, source=None)
    channel = FakeChannel(*[Delivery(failed=1, retry=True)] * 5)
    now = datetime.now(UTC)
    for minutes in (0, 1, 6, 21, 81):
        await run_once(clean_db, channel, now + timedelta(minutes=minutes, seconds=1))
    session.expunge_all()
    event = await session.scalar(select(OutboxEvent))
    assert (event.status, event.attempts) == ("failed", 5)
    assert len(channel.sent) == 5


async def test_retry_waits_for_its_time(session, preset, clean_db):
    await create_lead(session, preset, COMPLETE, source=None)
    channel = FakeChannel(Delivery(failed=1, retry=True))
    now = datetime.now(UTC)
    await run_once(clean_db, channel, now)
    assert await run_once(clean_db, channel, now + timedelta(seconds=30)) == 0


async def test_no_device_means_skipped_not_retried(session, preset, clean_db):
    await create_lead(session, preset, COMPLETE, source=None)
    await run_once(clean_db, FakeChannel(Delivery()), datetime.now(UTC))
    session.expunge_all()
    assert (await session.scalar(select(OutboxEvent))).status == "skipped"


# --- the push channel ------------------------------------------------------------


@pytest.fixture
def pushed(monkeypatch):
    """Replaces the network call; records what would have been sent."""
    calls = []

    def fake_send(subscription, payload, settings):
        calls.append((subscription, json.loads(payload)))
        outcome = fake_send.outcome
        if outcome:
            raise WebPushException(
                "push failed", response=type("R", (), {"status_code": outcome})()
            )

    fake_send.outcome = None
    monkeypatch.setattr(push_module, "send_webpush", fake_send)
    return fake_send, calls


async def add_subscription(session, endpoint=FCM):
    session.add(PushSubscription(endpoint=endpoint, p256dh="BPkey", auth="authsecret"))
    await session.commit()


async def test_push_sends_car_only_payload(session, preset, clean_db, pushed):
    from app.db.session import create_session_factory

    _, calls = pushed
    await add_subscription(session)
    created = await create_lead(session, preset, COMPLETE, source=None)
    channel = PushChannel(make_settings(**KEYS), create_session_factory(clean_db))
    note = build("new_lead", created, 0, MESSAGES, make_settings())
    result = await channel.send(note)
    assert result.delivered == 1
    payload = calls[0][1]
    assert payload == {
        "title": "New lead: 2019 Toyota Camry",
        "body": "$21,500 · No photos yet",
        "url": f"/app/leads/{created.id}",
        "tag": f"lead-{created.id}",
    }
    session.expunge_all()
    assert (await session.scalar(select(PushSubscription))).last_success_at is not None


async def test_gone_subscription_is_removed(session, clean_db, pushed):
    from app.db.session import create_session_factory

    send, _ = pushed
    send.outcome = 410
    await add_subscription(session)
    channel = PushChannel(make_settings(**KEYS), create_session_factory(clean_db))
    result = await channel.send(build("new_lead", lead(), 0, MESSAGES, make_settings()))
    assert (result.failed, result.retry) == (1, False)
    session.expunge_all()
    assert await session.scalar(select(PushSubscription)) is None


async def test_temporary_failure_is_counted_and_retried(session, clean_db, pushed):
    from app.db.session import create_session_factory

    send, _ = pushed
    send.outcome = 500
    await add_subscription(session)
    channel = PushChannel(make_settings(**KEYS), create_session_factory(clean_db))
    result = await channel.send(build("new_lead", lead(), 0, MESSAGES, make_settings()))
    assert result.retry
    session.expunge_all()
    assert (await session.scalar(select(PushSubscription))).failure_count == 1


@pytest.mark.parametrize(
    ("endpoint", "allowed"),
    [
        ("https://fcm.googleapis.com/fcm/send/x", True),
        ("https://web.push.apple.com/QF2", True),
        ("https://updates.push.services.mozilla.com/wpush/v2/x", True),
        ("https://wns2-bl2p.notify.windows.com/w/?token=x", True),
        ("http://fcm.googleapis.com/fcm/send/x", False),
        ("https://evil.example/fcm.googleapis.com", False),
        ("https://fcm.googleapis.com.evil.example/x", False),
        ("https://169.254.169.254/latest/meta-data", False),
    ],
)
def test_only_real_push_services_are_accepted(endpoint, allowed):
    assert allowed_endpoint(endpoint) is allowed


# --- settings and registry -------------------------------------------------------


def test_channels_come_from_settings():
    assert make_settings(notify_channels="push, ").notify_channels == ["push"]
    with pytest.raises(UnknownChannel):
        create_channels(make_settings(notify_channels="pager"), None)
    # Without keys, development runs with push switched off.
    assert create_channels(make_settings(), None) == []


def test_malformed_vapid_keys_are_rejected():
    with pytest.raises(ValidationError, match="VAPID_PUBLIC_KEY"):
        make_settings(vapid_public_key="not-a-key")
    with pytest.raises(ValidationError, match="VAPID_SUBJECT"):
        make_settings(vapid_subject="owner@example.com")


# --- the owner's push API ---------------------------------------------------------


@pytest.fixture
async def owner(client_for):
    client = client_for(owner_password=PASSWORD, **KEYS)
    await sign_in(client, PASSWORD)
    return client


async def test_subscribe_test_and_unsubscribe(owner, pushed, clean_db):
    status = (await owner.get("/api/owner/push")).json()
    assert status["configured"] and status["problem"] and status["devices"] == 0
    assert status["publicKey"] == KEYS["vapid_public_key"]

    assert (await owner.post("/api/owner/push/subscriptions", json=SUBSCRIPTION)).status_code == 201
    test = await owner.post("/api/owner/push/test", json={"endpoint": FCM})
    assert test.json()["delivered"] == 1
    assert pushed[1][0][1]["title"] == "Car Buyout · New vehicle request"
    status = (await owner.get("/api/owner/push")).json()
    assert (status["devices"], status["problem"]) == (1, False)

    await owner.post("/api/owner/push/unsubscribe", json={"endpoint": FCM})
    assert (await owner.get("/api/owner/push")).json()["devices"] == 0


async def test_foreign_endpoints_are_refused(owner, clean_db):
    body = {**SUBSCRIPTION, "endpoint": "https://evil.example/collect"}
    response = await owner.post("/api/owner/push/subscriptions", json=body)
    assert response.status_code == 422


async def test_test_push_without_a_device_says_so(owner, clean_db):
    assert (await owner.post("/api/owner/push/test", json={})).status_code == 409


async def test_failing_device_raises_the_warning(owner, pushed, clean_db):
    await owner.post("/api/owner/push/subscriptions", json=SUBSCRIPTION)
    pushed[0].outcome = 500
    await owner.post("/api/owner/push/test", json={})
    assert (await owner.get("/api/owner/push")).json()["problem"] is True
