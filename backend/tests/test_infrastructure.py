from concurrent.futures import ThreadPoolExecutor

import pytest
from app.infrastructure.cache import TTLCache
from app.infrastructure.retry import RetryPolicy, retry
from app.security.local_rate_limit import SlidingWindowLimiter


def test_cache_expiry_and_lru():
    now = [10.0]
    cache = TTLCache(2, clock=lambda: now[0])
    cache.put("first", 1, 10)
    cache.put("second", 2, 10)
    assert cache.get("first") == 1
    cache.put("third", 3, 20)
    with pytest.raises(KeyError):
        cache.get("second")
    now[0] = 20
    with pytest.raises(KeyError):
        cache.get("first")
    assert cache.get("third") == 3
    assert len(cache) == 1


def test_cache_replacement_none_and_invalidation():
    cache = TTLCache(1)
    cache.put("sample", 1, 10)
    cache.put("sample", None, 10)
    assert cache.get("sample") is None
    assert cache.invalidate("sample")
    assert not cache.invalidate("sample")
    cache.put("sample", 2, 10)
    cache.clear()
    assert len(cache) == 0


def test_cache_has_bounded_size_with_parallel_writers():
    cache = TTLCache(8)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda number: cache.put(number, number, 60), range(100)))
    assert len(cache) == 8


@pytest.mark.parametrize("ttl", [0, -1, float("nan"), float("inf"), True])
def test_bad_cache_ttl(ttl):
    with pytest.raises(ValueError):
        TTLCache(1).put("key", "value", ttl)


def test_retry_backoff_cap_and_success():
    calls, delays = [], []

    def operation():
        calls.append(1)
        if len(calls) < 4:
            raise ConnectionError("temporary")
        return "done"

    result = retry(
        operation,
        retryable=lambda error: isinstance(error, ConnectionError),
        policy=RetryPolicy(attempts=4, initial_delay=1, max_delay=2),
        sleep=delays.append,
        jitter=lambda: 0.5,
    )
    assert result == "done"
    assert delays == [0.5, 1, 1]


def test_retry_preserves_final_exception():
    delays = []
    original = ConnectionError("offline")

    def operation():
        raise original

    with pytest.raises(ConnectionError) as raised:
        retry(
            operation,
            retryable=lambda error: True,
            sleep=delays.append,
            jitter=lambda: 1,
        )
    assert raised.value is original
    assert len(delays) == 2


@pytest.mark.parametrize(
    "error", [ValueError("invalid"), KeyboardInterrupt(), SystemExit()]
)
def test_nonretryable_and_base_exceptions_are_not_retried(error):
    delays = []

    def operation():
        raise error

    with pytest.raises(type(error)):
        retry(
            operation,
            retryable=lambda exc: isinstance(exc, ConnectionError),
            sleep=delays.append,
        )
    assert delays == []


@pytest.mark.parametrize(
    "settings",
    [
        {"attempts": 0},
        {"attempts": True},
        {"attempts": 21},
        {"initial_delay": -1},
        {"max_delay": float("inf")},
        {"initial_delay": 10, "max_delay": 1},
    ],
)
def test_bad_retry_policy(settings):
    with pytest.raises(ValueError):
        RetryPolicy(**settings)


def test_limiter_fails_closed_at_capacity():
    now = [0.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0], max_keys=2, cleanup_interval=1)
    assert limiter.allow("first", 1, 10)
    assert limiter.allow("second", 1, 10)
    assert not limiter.allow("third", 1, 10)
    assert not limiter.allow("first", 1, 10)
    assert limiter.tracked_keys() == 2
    now[0] = 10
    assert limiter.allow("third", 1, 10)
    assert limiter.tracked_keys() == 1


def test_full_limiter_reclaims_expired_keys_before_periodic_cleanup():
    now = [0.0]
    limiter = SlidingWindowLimiter(
        clock=lambda: now[0], max_keys=1, cleanup_interval=60
    )
    assert limiter.allow("first", 1, 1)
    now[0] = 2
    assert limiter.allow("second", 1, 1)
    assert limiter.tracked_keys() == 1


@pytest.mark.parametrize(
    "limit,window", [(float("nan"), 60), (5, float("nan")), (True, 60), (5, 0)]
)
def test_limiter_rejects_invalid_limits(limit, window):
    with pytest.raises(ValueError):
        SlidingWindowLimiter().allow("sample", limit, window)
