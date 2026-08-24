"""A small in-memory rate limiter for single-process deployments."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable


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
    ):
        if cleanup_interval <= 0:
            raise ValueError("cleanup_interval must be positive")
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

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
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
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        now = self._clock()
        with self._lock:
            self._cleanup(now)
            window = self._windows.get(key)
            if window is None:
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
