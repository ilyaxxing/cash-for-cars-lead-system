import re

from app.config import BASE_DIR
from app.web.privacy import TAG, fill
from tests.test_branding import logo

TEMPLATE = "Hello {name}\n- Mail: {address}\n- Phone: {phone} or {address}\nPlain line\n"


def test_lines_with_only_empty_placeholders_are_dropped():
    assert fill(TEMPLATE, {"name": "Ann", "address": "", "phone": ""}) == "Hello Ann\nPlain line\n"


def test_values_cannot_inject_markdown():
    assert fill("By {name}\n", {"name": "**[x](javascript:alert(1))**"}) == (
        "By \\*\\*\\[x\\]\\(javascript:alert\\(1\\)\\)\\*\\*\n"
    )


async def test_policy_page_is_filled_from_settings(client_for):
    client = client_for(
        operator_name="Example Auto LLC",
        operator_email="privacy@example.com",
        brand_phone="(415) 555-0142",
        policy_effective_date="2026-11-01",
        public_url="https://buyer.example.com",
    )
    response = await client.get("/privacy")
    assert response.status_code == 200
    page = response.text
    assert "Example Auto LLC" in page
    assert "privacy@example.com" in page
    assert "(415) 555-0142" in page
    assert "Last updated: 2026-11-01" in page
    assert "https://buyer.example.com" in page
    assert "<strong>90 days after the inquiry is closed</strong>" in page
    assert "Mail:" not in page  # no mailing address configured


async def test_policy_escapes_html_in_settings(client_for):
    response = await client_for(operator_name="<script>alert(1)</script>").get("/privacy")
    assert "<script>alert(1)</script>" not in response.text


async def test_policy_falls_back_to_brand_in_development(client_for):
    response = await client_for(brand_name="Rapid Cash Cars").get("/privacy")
    assert "Rapid Cash Cars" in response.text
    assert "Last updated" not in response.text


def test_the_mark_is_the_apps_price_tag():
    glyph = (BASE_DIR / "frontend" / "src" / "shared" / "TagGlyph.svelte").read_text()
    path = re.search(r'd="([^"]+)"', glyph).group(1)
    assert f'd="{path}"' in TAG


async def test_policy_page_wears_the_client_color(client_for):
    page = (await client_for(brand_color="#FF8A00").get("/privacy")).text
    assert "--accent:#FF8A00" in page
    assert TAG in page
    assert "#C7F747" not in page  # nothing left in the designs' lime


async def test_policy_page_shows_the_client_logo(client_for, tmp_path):
    page = (
        await client_for(brand_logo=logo(tmp_path), brand_name="Rapid Cash Cars").get("/privacy")
    ).text
    assert '<img class="logo" src="/brand/logo.png?v=' in page
    assert "<span>Rapid Cash Cars</span>" in page
    assert TAG not in page


async def test_a_wordmark_logo_stands_alone(client_for, tmp_path):
    wide = logo(tmp_path, size=(900, 200))
    page = (await client_for(brand_logo=wide, brand_name="Rapid Cash Cars").get("/privacy")).text
    assert 'class="logo wordmark"' in page
    assert 'alt="Rapid Cash Cars"' in page
    assert "<span>Rapid Cash Cars</span>" not in page
