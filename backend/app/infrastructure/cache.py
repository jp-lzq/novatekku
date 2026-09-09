import math
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from threading import Lock
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    def __init__(self, capacity: int, *, clock: Callable[[], float] = time.monotonic):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self._clock = clock
        self._entries: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._lock = Lock()

    def _expire(self, now: float) -> None:
        for key in [
            key for key, (deadline, _) in self._entries.items() if deadline <= now
        ]:
            del self._entries[key]

    def put(self, key: K, value: V, ttl: float) -> None:
        if isinstance(ttl, bool) or not math.isfinite(ttl) or ttl <= 0:
            raise ValueError("ttl must be finite and positive")
        with self._lock:
            now = self._clock()
            self._expire(now)
            self._entries[key] = (now + ttl, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.capacity:
                self._entries.popitem(last=False)

    def get(self, key: K) -> V:
        with self._lock:
            self._expire(self._clock())
            _, value = self._entries[key]
            self._entries.move_to_end(key)
            return value

    def invalidate(self, key: K) -> bool:
        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            self._expire(self._clock())
            return len(self._entries)
