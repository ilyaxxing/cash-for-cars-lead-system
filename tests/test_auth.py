import pytest

from app.services import auth
from app.services.ratelimit import RateLimiter
from tests.conftest import OWN_PASSWORD, sign_in

pytestmark = pytest.mark.usefixtures("clean_db")

PASSWORD = "owner-pass-2026"  # gitleaks:allow (test-only password)


@pytest.fixture
def client(client_for):
    return client_for(owner_password=PASSWORD)


async def login(client, password=PASSWORD):
    return await client.post("/api/auth/login", json={"password": password})


async def test_dashboard_api_needs_a_session(client):
    assert (await client.get("/api/owner/leads")).status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_login_sets_a_long_lived_http_only_cookie(client):
    response = await login(client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert f"max-age={365 * 24 * 3600}" in cookie
    assert (await client.get("/api/auth/me")).json()["authenticated"] is True


async def test_wrong_password_is_refused(client):
    response = await login(client, "nope")
    assert response.status_code == 401
    assert response.json() == {"error": "wrong_password"}


async def test_guessing_is_slowed_down(client):
    for _ in range(10):
        await login(client, "guess")
    response = await login(client)  # even the right password waits now
    assert response.status_code == 429


async def test_missing_owner_password_is_explained(client_for):
    response = await login(client_for(owner_password=""))
    assert response.json() == {"error": "not_configured"}


async def test_logout_ends_the_session(client):
    await login(client)
    await client.post("/api/auth/logout")
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_password_change_signs_out_other_devices(client_for):
    phone = client_for(owner_password=PASSWORD)
    laptop = client_for(owner_password=PASSWORD)
    await login(phone)
    await login(laptop)
    response = await phone.post(
        "/api/auth/password", json={"current": PASSWORD, "new": "brand-new-7"}
    )
    assert response.status_code == 200
    assert (await phone.get("/api/auth/me")).status_code == 200
    assert (await laptop.get("/api/auth/me")).status_code == 401
    assert (await login(laptop, PASSWORD)).status_code == 401
    assert (await login(laptop, "brand-new-7")).status_code == 200


@pytest.mark.parametrize(
    ("current", "new", "error"),
    [
        ("wrong", "brand-new-7", "wrong_current"),
        (OWN_PASSWORD, "short1", "weak"),
        (OWN_PASSWORD, "no-digits-here", "weak"),
        (OWN_PASSWORD, OWN_PASSWORD, "same"),
        # The password that was handed over never comes back.
        (OWN_PASSWORD, PASSWORD, "given"),
    ],
)
async def test_password_rules(client, current, new, error):
    await sign_in(client, PASSWORD)
    response = await client.post("/api/auth/password", json={"current": current, "new": new})
    assert response.status_code == 422
    assert response.json() == {"error": error}


async def test_the_password_handed_over_opens_only_the_password_change(client):
    response = await login(client)
    assert response.json() == {"ok": True, "mustChangePassword": True}
    assert (await client.get("/api/auth/me")).json()["mustChangePassword"] is True
    for path in ("/api/owner/leads", "/api/owner/stats", "/api/owner/push"):
        response = await client.get(path)
        assert response.status_code == 403
        assert response.json() == {"detail": "password_change_required"}

    # No current password asked: the owner has just signed in with it.
    for new, error in (("short1", "weak"), (PASSWORD, "given")):
        response = await client.post("/api/auth/password", json={"new": new})
        assert response.json() == {"error": error}
    assert (await client.post("/api/auth/password", json={"new": OWN_PASSWORD})).status_code == 200
    assert (await client.get("/api/auth/me")).json()["mustChangePassword"] is False
    assert (await client.get("/api/owner/leads")).status_code == 200
    assert (await login(client, PASSWORD)).status_code == 401
    assert (await login(client, OWN_PASSWORD)).json() == {"ok": True, "mustChangePassword": False}


async def test_changing_owner_password_env_resets_the_dashboard_password(client_for):
    first = client_for(owner_password=PASSWORD)
    await login(first)
    await first.post("/api/auth/password", json={"current": PASSWORD, "new": "forgotten-1"})

    # The owner forgot the new password; the operator sets a fresh one in .env.
    restarted = client_for(owner_password="fresh-start-2")
    assert (await login(restarted, "forgotten-1")).status_code == 401
    # The fresh one is handed over too, so it asks for an own password again.
    assert (await login(restarted, "fresh-start-2")).json()["mustChangePassword"] is True
    assert (await restarted.get("/api/owner/leads")).status_code == 403
    assert (await first.get("/api/auth/me")).status_code == 401


async def test_a_reset_signs_every_device_out_when_the_app_restarts(client_for):
    phone = client_for(owner_password=PASSWORD)
    await sign_in(phone, PASSWORD)
    # The same phone after a deploy with a new OWNER_PASSWORD, before anyone signs in.
    restarted = client_for(owner_password="fresh-start-2")
    restarted.cookies = phone.cookies
    assert (await restarted.get("/api/owner/leads")).status_code == 401


async def test_cross_site_posts_are_refused(client):
    response = await client.post(
        "/api/auth/login", json={"password": PASSWORD}, headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403


def test_rate_limiter_window():
    now = [0.0]
    limiter = RateLimiter(limit=2, window_seconds=10, clock=lambda: now[0])
    assert limiter.hit("ip") and limiter.hit("ip")
    assert not limiter.hit("ip") and limiter.blocked("ip")
    now[0] = 10.5
    assert not limiter.blocked("ip")


def test_only_a_hash_of_the_session_token_is_stored():
    assert auth._token_id("abc") != "abc"
    assert len(auth._token_id("abc")) == 64
