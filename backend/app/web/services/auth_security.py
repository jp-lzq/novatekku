import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class AuthRateLimiter:
    """Redis first, process-local fallback rate limiter for authentication endpoints."""

    def __init__(self):
        self._redis: Redis | None = None
        self._redis_retry_at = 0.0
        self._fallback: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @staticmethod
    def _key(scope: str, identifier: str) -> str:
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        return f"nova:auth-rate:{scope}:{digest}"

    def _redis_client(self) -> Redis | None:
        if not settings.redis_url or time.monotonic() < self._redis_retry_at:
            return None
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
            )
        return self._redis

    def _check_redis(self, key: str, limit: int, window_seconds: int) -> bool | None:
        client = self._redis_client()
        if client is None:
            return None
        try:
            with client.pipeline() as pipeline:
                pipeline.incr(key)
                pipeline.expire(key, window_seconds, nx=True)
                count, _ = pipeline.execute()
            return int(count) <= limit
        except RedisError:
            self._redis = None
            self._redis_retry_at = time.monotonic() + 60
            return None

    def _check_fallback(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            attempts = self._fallback[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            attempts.append(now)
            return len(attempts) <= limit

    def check(self, scope: str, identifier: str, limit: int) -> None:
        window_seconds = settings.auth_rate_limit_window_seconds
        key = self._key(scope, identifier)
        allowed = self._check_redis(key, limit, window_seconds)
        if allowed is None:
            allowed = self._check_fallback(key, limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many authentication attempts",
                headers={"Retry-After": str(window_seconds)},
            )

    def reset_for_tests(self) -> None:
        with self._lock:
            self._fallback.clear()
        self._redis = None
        self._redis_retry_at = time.monotonic() + 60


auth_rate_limiter = AuthRateLimiter()
