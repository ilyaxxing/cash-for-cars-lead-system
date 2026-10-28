"""Interface text lookup.

All text a person reads lives in locales/<locale>.json. Code refers to it by
dotted keys ("preset.fields.make.label") and fills {placeholders} at render
time. The server needs only a little of it (push notifications, the privacy
page); the full file is handed to the frontend with the page.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from babel import Locale, UnknownLocaleError
from babel.numbers import format_currency

PLACEHOLDER = re.compile(r"\{(\w+)\}")


class LocaleError(Exception):
    """The locale file is missing or broken; raised at startup."""


class Messages:
    def __init__(self, locale: str, data: Mapping[str, Any]) -> None:
        self.locale = locale
        self.data = data

    def get(self, key: str) -> str | None:
        node: Any = self.data
        for part in key.split("."):
            if not isinstance(node, Mapping) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, str) else None

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def t(self, key: str, **params: Any) -> str:
        """Text for key with {placeholders} filled. Unknown keys come back as the key.

        Returning the key instead of raising keeps a missing translation
        visible on screen without taking a page down.
        """
        text = self.get(key)
        if text is None:
            return key
        return PLACEHOLDER.sub(lambda m: str(params.get(m.group(1), m.group(0))), text)


def format_money(amount: int, currency: str, locale: str, region: str) -> str:
    """A whole amount the way the country writes it: "$21,500", "850 000 ₽".

    The same as the browser's Intl formatting in the form and the dashboard,
    so a price reads alike in a notification and on screen.
    """
    language = locale.replace("-", "_")  # zh-Hant: Babel's zh_Hant
    try:
        place = Locale.parse(f"{language}_{region}")
    except (UnknownLocaleError, ValueError):
        place = Locale.parse(language)
    whole = re.sub(r"\.0+", "", place.currency_formats["standard"].pattern)
    return format_currency(amount, currency, format=whole, locale=place, currency_digits=False)


def text_keys(data: Mapping[str, Any], prefix: str = "") -> dict[str, str]:
    """Every text in a locale, by dotted key."""
    found: dict[str, str] = {}
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            found.update(text_keys(value, dotted))
        elif isinstance(value, str):
            found[dotted] = value
    return found


def translation_problems(reference: Messages, messages: Messages) -> list[str]:
    """What a translation lacks against the reference locale, one line each.

    A missing text would show its key on screen, and a placeholder that is
    not the reference's would never be filled in.
    """
    problems = []
    for key, text in text_keys(reference.data).items():
        mine = messages.get(key)
        if mine is None:
            problems.append(f"missing: {key}")
            continue
        expected, given = set(PLACEHOLDER.findall(text)), set(PLACEHOLDER.findall(mine))
        if expected != given:
            wanted = ", ".join(f"{{{name}}}" for name in sorted(expected)) or "none"
            problems.append(f"{key}: placeholders should be {wanted}")
    return problems


def load_messages(locales_dir: Path, locale: str, extra: Path | None = None) -> Messages:
    """Texts for `locale`: the shipped file, with a client's own file laid over it.

    The client's file (LOCALE_FILE) may change a few texts or translate them
    all; for a locale nothing ships for, it is the whole set.
    """
    path = locales_dir / f"{locale}.json"
    if extra is not None and not path.exists():
        return Messages(locale, _read_locale(extra, "LOCALE_FILE"))
    data = _read_locale(path, f"LOCALE={locale!r}")
    if extra is not None:
        data = _laid_over(data, _read_locale(extra, "LOCALE_FILE"))
    return Messages(locale, data)


def _read_locale(path: Path, setting: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LocaleError(f"locale file {path} not found ({setting})") from exc
    except json.JSONDecodeError as exc:
        raise LocaleError(f"locale file {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LocaleError(f"locale file {path} must contain a JSON object")
    return data


def _laid_over(base: dict[str, Any], top: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in top.items():
        below = merged.get(key)
        both_groups = isinstance(below, dict) and isinstance(value, dict)
        merged[key] = _laid_over(below, value) if both_groups else value
    return merged
