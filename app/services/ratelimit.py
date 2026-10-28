"""In-memory sliding-window rate limits.

The app runs as a single process (one replica), so counters in memory are
enough and nothing about a visitor, not even the IP address, is written to
the database or the logs. A restart resets the counters, which is acceptable
for what they guard against: password guessing and form spam.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic
    ):
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def _trim(self, key: str, now: float) -> deque[float]:
        hits = self.hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if not hits:
            del self.hits[key]
            return deque()
        return hits

    def blocked(self, key: str) -> bool:
        return len(self._trim(key, self.clock())) >= self.limit

    def hit(self, key: str) -> bool:
        """Record an attempt. Returns False when the key is over the limit."""
        now = self.clock()
        hits = self._trim(key, now)
        if len(hits) >= self.limit:
            return False
        self.hits[key].append(now)
        return True

    def reset(self, key: str) -> None:
        self.hits.pop(key, None)
