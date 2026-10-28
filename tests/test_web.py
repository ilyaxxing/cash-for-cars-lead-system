import json
import re

from app.web import health
from tests.conftest import vapid_keys

SECRETS = {
    "secret_key": "super-secret-signing-key-0123456789abcdef",
    "owner_password": "owner-password-do-not-leak",
    "s3_secret_access_key": "bucket-secret-do-not-leak",
    "vapid_private_key": vapid_keys()["vapid_private_key"],
}


def embedded_config(html: str) -> dict:
    match = re.search(r'<script id="app-config" type="application/json">(.*?)</script>', html)
    assert match, "config block missing"
    return json.loads(match.group(1))


async def test_health_reports_version_and_revision(client_for, database_url):
    client = client_for(git_sha="abc1234")
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "version": "abc1234", "revision": health.expected_revision()}


async def test_health_fails_while_migrations_are_pending(client_for, database_url, monkeypatch):
    monkeypatch.setattr(health, "expected_revision", lambda: "some-newer-revision")
    response = await client_for().get("/healthz")
    assert response.status_code == 503
    assert response.json()["reason"] == "migrations"


async def test_health_fails_without_database(client_for):
    client = client_for(database_url="postgresql://nobody@127.0.0.1:1/nothing")
    response = await client.get("/healthz")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "reason": "database"}


async def test_form_page_carries_brand_preset_and_texts(client_for):
    response = await client_for(brand_name="Rapid Cash Cars").get("/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    config = embedded_config(response.text)
    assert config["brand"]["name"] == "Rapid Cash Cars"
    assert config["preset"]["id"] == "us-car-buyout"
    assert config["messages"]["statuses"]["bought"] == "Purchased"


async def test_config_cannot_break_out_of_the_script_tag(client_for):
    response = await client_for(brand_name="</script><img src=x onerror=alert(1)>").get("/")
    assert "</script><img" not in response.text
    assert embedded_config(response.text)["brand"]["name"].startswith("</script>")


async def test_browser_config_holds_no_secrets(client_for):
    client = client_for(**SECRETS)
    pages = [(await client.get("/")).text, (await client.get("/api/config")).text]
    for page in pages:
        for secret in SECRETS.values():
            assert secret not in page


async def test_business_card_link_tags_the_source(client_for):
    response = await client_for().get("/v")
    assert response.status_code == 302
    assert response.headers["location"] == "/?src=card"


async def test_dashboard_routes_serve_the_dashboard_app(client_for):
    client = client_for()
    for path in ("/app", "/app/leads/42", "/app/settings"):
        response = await client.get(path)
        assert response.status_code == 200
        assert "dashboard" in response.text


async def test_missing_build_is_explained(client_for, tmp_path):
    response = await client_for(frontend_dist=tmp_path / "nowhere").get("/")
    assert response.status_code == 503
    assert "npm run build" in response.text


async def test_manifest_installs_under_the_brand(client_for):
    response = await client_for(brand_name="Rapid Cash Cars").get("/app/manifest.webmanifest")
    manifest = response.json()
    assert response.headers["content-type"].startswith("application/manifest+json")
    assert manifest["name"] == "Rapid Cash Cars"
    assert manifest["short_name"] == "Rapid"
    assert manifest["scope"] == manifest["start_url"] == "/app/"
    assert {icon["sizes"] for icon in manifest["icons"]} == {"192x192", "512x512"}


async def test_service_worker_is_served_for_the_dashboard_scope(client_for):
    response = await client_for().get("/app/sw.js")
    assert response.status_code == 200
    assert response.headers["service-worker-allowed"] == "/app/"
    assert response.headers["cache-control"] == "no-cache"


async def test_icons_are_not_swallowed_by_the_dashboard_route(client_for):
    response = await client_for().get("/app/icons/icon-192.png")
    assert response.content.startswith(b"\x89PNG")
