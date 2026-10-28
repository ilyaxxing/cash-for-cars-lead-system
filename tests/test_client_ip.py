"""Rate limits key on the visitor's real address behind the hosting proxy.

The app runs as the Dockerfile starts it: uvicorn trusting every forwarded
header (--proxy-headers --forwarded-allow-ips='*'). Railway rebuilds
X-Forwarded-For itself (checked live), but a proxy that passes a client's own
value through would hand it to uvicorn as the address; the limits must not care.
"""

from itertools import count

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.main import create_app
from tests.conftest import make_settings
from tests.test_answers import COMPLETE

pytestmark = pytest.mark.usefixtures("clean_db")

PASSWORD = "owner-pass-2026"  # gitleaks:allow (test-only password)
VISITOR = "203.0.113.7"
forged = (f"198.18.0.{n}" for n in count(1))


@pytest.fixture
async def behind_proxy(frontend_dist):
    apps = []

    def build(**overrides) -> AsyncClient:
        app = create_app(
            make_settings(frontend_dist=frontend_dist, owner_password=PASSWORD, **overrides)
        )
        apps.append(app)
        proxied = ProxyHeadersMiddleware(app, trusted_hosts="*")
        return AsyncClient(transport=ASGITransport(app=proxied), base_url="http://test")

    yield build
    for app in apps:
        await app.state.engine.dispose()


def headers(real: str = VISITOR) -> dict[str, str]:
    """What the edge sends: the real address, plus whatever the client forged."""
    return {"X-Real-IP": real, "X-Forwarded-For": next(forged)}


async def new_lead(client, real=VISITOR):
    return await client.post("/api/leads", json={"answers": COMPLETE}, headers=headers(real))


async def test_without_the_header_a_forged_forwarded_for_escapes_the_limit(behind_proxy):
    # Why CLIENT_IP_HEADER exists: the connecting address is the client's choice.
    client = behind_proxy()
    statuses = {(await new_lead(client)).status_code for _ in range(12)}
    assert statuses == {201}


async def test_forged_forwarded_for_does_not_reset_the_lead_limit(behind_proxy):
    client = behind_proxy(client_ip_header="X-Real-IP")
    for _ in range(10):
        assert (await new_lead(client)).status_code == 201
    assert (await new_lead(client)).status_code == 429
    # Another visitor still gets through.
    assert (await new_lead(client, real="198.51.100.4")).status_code == 201


async def test_password_guessing_cannot_hide_behind_forged_headers(behind_proxy):
    client = behind_proxy(client_ip_header="X-Real-IP")
    for _ in range(10):
        await client.post("/api/auth/login", json={"password": "guess"}, headers=headers())
    response = await client.post("/api/auth/login", json={"password": PASSWORD}, headers=headers())
    assert response.status_code == 429


async def test_a_value_that_is_not_an_address_falls_back_to_the_connection(behind_proxy):
    client = behind_proxy(client_ip_header="X-Real-IP")
    response = await new_lead(client, real="<script>")
    assert response.status_code == 201


@pytest.mark.parametrize("value", ["X-Forwarded-For", "x-forwarded-for", "X Real IP", "a" * 65])
def test_unusable_header_names_are_refused(value):
    with pytest.raises(ValidationError, match="CLIENT_IP_HEADER"):
        make_settings(client_ip_header=value)
