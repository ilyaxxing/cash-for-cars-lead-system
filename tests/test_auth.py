import pytest

from app.services import auth
from app.services.ratelimit import RateLimiter

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
        (PASSWORD, "short1", "weak"),
        (PASSWORD, "no-digits-here", "weak"),
        (PASSWORD, PASSWORD, "same"),
    ],
)
async def test_password_rules(client, current, new, error):
    await login(client)
    response = await client.post("/api/auth/password", json={"current": current, "new": new})
    assert response.status_code == 422
    assert response.json() == {"error": error}


async def test_changing_owner_password_env_resets_the_dashboard_password(client_for):
    first = client_for(owner_password=PASSWORD)
    await login(first)
    await first.post("/api/auth/password", json={"current": PASSWORD, "new": "forgotten-1"})

    # The owner forgot the new password; the operator sets a fresh one in .env.
    restarted = client_for(owner_password="fresh-start-2")
    assert (await login(restarted, "forgotten-1")).status_code == 401
    assert (await login(restarted, "fresh-start-2")).status_code == 200
    assert (await first.get("/api/auth/me")).status_code == 401


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
