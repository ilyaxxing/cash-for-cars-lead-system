"""Numbers for the Statistics screen.

Definitions follow the design:
- a period is the last 7 days, the last 30 days (both up to today, in the
  owner's time zone) or all time;
- "this week" always starts on Monday, whatever the period;
- conversion = leads purchased / leads received, both counted over leads
  received in the period;
- sources group leads by the source frozen on each lead.

Kept as plain functions over (created_at, status, source) rows so they can
be tested without a database.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.db.models import STATUS_BOUGHT

PERIODS = {"7": 7, "30": 30, "all": None}


@dataclass(frozen=True)
class Row:
    created_at: datetime
    status: str
    source: str


def _midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=tz)


def period_start(period: str, now: datetime, tz: ZoneInfo) -> datetime | None:
    days = PERIODS[period]
    if days is None:
        return None
    return _midnight(now.astimezone(tz).date() - timedelta(days=days - 1), tz)


def week_start(now: datetime, tz: ZoneInfo) -> datetime:
    today = now.astimezone(tz).date()
    return _midnight(today - timedelta(days=today.weekday()), tz)


def _buckets(
    rows: list[Row], period: str, start: datetime | None, now: datetime, tz: ZoneInfo
) -> list[dict[str, Any]]:
    today = now.astimezone(tz).date()
    if period == "7":
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        edges = [(_midnight(d, tz), _midnight(d + timedelta(days=1), tz)) for d in days]
    else:
        if not rows and start is None:
            return []
        first = min(r.created_at for r in rows) if rows else start
        begin = max(start, first) if start else first
        monday = begin.astimezone(tz).date()
        monday -= timedelta(days=monday.weekday())
        current = today - timedelta(days=today.weekday())
        edges = []
        while monday <= current:
            edges.append((_midnight(monday, tz), _midnight(monday + timedelta(days=7), tz)))
            monday += timedelta(days=7)
    result = []
    for low, high in edges:
        inside = [r for r in rows if low <= r.created_at < high]
        result.append(
            {
                "start": low.date().isoformat(),
                "leads": len(inside),
                "purchased": sum(r.status == STATUS_BOUGHT for r in inside),
            }
        )
    return result


def compute(rows: list[Row], period: str, now: datetime, tz: ZoneInfo) -> dict[str, Any]:
    if period not in PERIODS:
        raise ValueError(f"unknown period {period!r}")
    start = period_start(period, now, tz)
    in_period = [r for r in rows if start is None or r.created_at >= start]
    bought = sum(r.status == STATUS_BOUGHT for r in in_period)

    received = Counter(r.source for r in in_period)
    purchased = Counter(r.source for r in in_period if r.status == STATUS_BOUGHT)
    sources = [
        {"source": source, "leads": count, "purchased": purchased[source]}
        for source, count in sorted(received.items(), key=lambda item: (-item[1], item[0]))
    ]
    first = min((r.created_at for r in rows), default=None)
    return {
        "period": period,
        "total": len(in_period),
        "week": sum(r.created_at >= week_start(now, tz) for r in rows),
        "weekStart": week_start(now, tz).date().isoformat(),
        "purchased": bought,
        "firstLeadAt": first.isoformat() if first else None,
        "sources": sources,
        "buckets": _buckets(in_period, period, start, now, tz),
    }
