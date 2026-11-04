"""A small in-process cache for public read endpoints.

Prices change only when a collection run finishes, but the price pages ask
for the same large lists on every visit.  Keeping each answer for a short time
(60 seconds by default) removes almost all repeated database work while a new
collection still shows up within a minute.  Only use it for data that is the
same for every visitor.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Hashable


class TTLCache:
    def __init__(self, ttl_seconds: float = 60.0, max_entries: int = 256, clock: Callable[[], float] = time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get_or_set(self, key: Hashable, compute: Callable[[], Any]) -> Any:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry[0] > now:
                self._entries.move_to_end(key)
                self.hits += 1
                return entry[1]
        value = compute()  # outside the lock: a slow query must not block other keys
        with self._lock:
            self.misses += 1
            self._entries[key] = (self._clock() + self.ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


# shared by the public price endpoints
PUBLIC_PRICE_CACHE = TTLCache(ttl_seconds=60, max_entries=256)
