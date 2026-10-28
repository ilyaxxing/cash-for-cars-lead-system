import pytest
from PIL import Image

from app import qr

BASE = "https://buy.example.com"


def test_print_parameters_live_in_one_place():
    assert (qr.ERROR_LEVEL, qr.BORDER, qr.MIN_MODULE_MM) == ("h", 4, 0.4)


@pytest.mark.parametrize(
    ("source", "url"),
    [("card", f"{BASE}/v"), ("parking", f"{BASE}/?src=parking")],
)
def test_links_match_the_routes(source, url):
    assert qr.link(BASE + "/", source) == url


def test_a_business_card_code_fits_comfortably():
    checked = qr.plan(BASE, "card")
    assert not checked.problems and not checked.warnings
    assert checked.modules == 33
    assert checked.module_mm > 0.6


def test_a_short_address_never_becomes_micro_qr():
    assert qr.plan("https://a.co", "card").modules >= 21


def test_too_small_for_print_is_refused():
    checked = qr.plan(BASE, "card", size_mm=10)
    assert checked.problems and "print limit" in checked.problems[0]
    with pytest.raises(ValueError):
        qr.write(checked, None)


def test_railway_address_is_refused():
    checked = qr.plan("https://car-buyout-production-1a2b.up.railway.app", "card")
    assert checked.problems and "client's own domain" in checked.problems[0]
    with pytest.raises(ValueError):
        qr.write(checked, None)


def test_unlabelled_source_is_flagged_and_labelled_one_is_not():
    assert "Other" in qr.plan(BASE, "parking").warnings[0]
    assert qr.plan(BASE, "parking", labels={"parking": "Parking lot"}).warnings == []


@pytest.mark.parametrize("source", ["Card", "with space", "кириллица", ""])
def test_bad_source_labels_are_refused(source):
    assert qr.plan(BASE, source).problems


def test_plain_http_is_refused():
    assert qr.plan("http://buy.example.com", "card").problems


def test_files_are_written_with_quiet_zone(tmp_path):
    checked = qr.plan(BASE, "flyer", labels={"flyer": "Flyers"})
    svg, png = qr.write(checked, tmp_path)
    assert svg.name == "buy.example.com-flyer.svg" and png.name == "buy.example.com-flyer.png"
    assert svg.read_text().startswith("<?xml")
    side = (checked.modules + 2 * qr.BORDER) * qr.PNG_SCALE
    assert Image.open(png).size == (side, side)
