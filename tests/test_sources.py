import logging

import pytest

from app.i18n import Messages
from app.services import sources
from app.services.sources import choose_source, parse_source, source_label

MESSAGES = Messages(
    "en", {"sources": {"card": "Business Card", "direct": "Other", "other": "Other"}}
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("card", "card"),
        (" Parking_Lot-2 ", "parking_lot-2"),
        (None, None),
        ("", None),
        ("has space", None),
        ("<script>", None),
        ("x" * 65, None),
    ],
)
def test_parse_source(raw, expected):
    assert parse_source(raw) == expected


@pytest.mark.parametrize(
    ("stored", "incoming", "expected"),
    [
        (None, None, "direct"),
        (None, "card", "card"),
        ("direct", "card", "card"),  # a label replaces the default
        ("card", "flyer", "card"),  # but never another label: first one wins
        ("card", None, "card"),
    ],
)
def test_first_meaningful_source_wins(stored, incoming, expected):
    assert choose_source(stored, incoming) == expected


def test_labels_come_from_settings_then_locale():
    assert source_label("parking", {"parking": "Parking lot"}, MESSAGES) == "Parking lot"
    assert source_label("card", {}, MESSAGES) == "Business Card"


def test_unknown_label_shows_as_other_and_is_logged_once(caplog, monkeypatch):
    monkeypatch.setattr(sources, "_warned", set())
    with caplog.at_level(logging.WARNING, logger="app.services.sources"):
        assert source_label("billboard", {}, MESSAGES) == "Other"
        assert source_label("billboard", {}, MESSAGES) == "Other"
    assert [record.getMessage() for record in caplog.records] == [
        "Source 'billboard' has no label in SOURCE_LABELS; shown as Other"
    ]
