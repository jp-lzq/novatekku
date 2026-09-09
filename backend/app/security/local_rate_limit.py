"""A small in-memory rate limiter for single-process deployments."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class _Window:
    events: deque[float]
    seconds: int


class SlidingWindowLimiter:
    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        *,
        cleanup_interval: float = 60.0,
        max_keys: int = 10_000,
    ):
        if (
            isinstance(cleanup_interval, bool)
            or not math.isfinite(cleanup_interval)
            or cleanup_interval <= 0
        ):
            raise ValueError("cleanup_interval must be positive")
        if type(max_keys) is not int or max_keys < 1:
            raise ValueError("max_keys must be a positive integer")
        self._max_keys = max_keys
        self._clock = clock
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = clock()
        self._windows: dict[str, _Window] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _expire(window: _Window, now: float) -> None:
        cutoff = now - window.seconds
        while window.events and window.events[0] <= cutoff:
            window.events.popleft()

    def _cleanup(self, now: float, *, force: bool = False) -> None:
        if not force and now - self._last_cleanup < self._cleanup_interval:
            return
        # Without this pass, one-off client IDs would stay in memory forever.
        expired: list[str] = []
        for key, window in self._windows.items():
            self._expire(window, now)
            if not window.events:
                expired.append(key)
        for key in expired:
            del self._windows[key]
        self._last_cleanup = now

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if not key:
            raise ValueError("key must not be empty")
        if (
            type(limit) is not int
            or type(window_seconds) is not int
            or limit < 1
            or window_seconds < 1
        ):
            raise ValueError("limit and window_seconds must be positive")
        with self._lock:
            now = self._clock()
            self._cleanup(now)
            window = self._windows.get(key)
            if window is None:
                if len(self._windows) >= self._max_keys:
                    self._cleanup(now, force=True)
                if len(self._windows) >= self._max_keys:
                    return False
                window = _Window(events=deque(), seconds=window_seconds)
                self._windows[key] = window
            elif window.seconds != window_seconds:
                raise ValueError("window_seconds must stay constant for a key")

            self._expire(window, now)
            if len(window.events) >= limit:
                return False
            window.events.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()
            self._last_cleanup = self._clock()

    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._windows)
