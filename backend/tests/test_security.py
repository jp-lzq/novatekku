from concurrent.futures import ThreadPoolExecutor
from datetime import timezone

import pytest

from app.security.local_rate_limit import SlidingWindowLimiter
from app.security.passwords import (
    hash_password,
    normalize_email,
    password_hash_needs_upgrade,
    verify_password,
)
from app.security.tokens import token_hash, utc_now


def test_password_round_trip_and_upgrade_detection() -> None:
    encoded = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)
    assert not password_hash_needs_upgrade(encoded)
    assert normalize_email(" Example@Email.COM ") == "example@email.com"


def test_password_verification_rejects_excessive_work_factor() -> None:
    encoded = "pbkdf2_sha256$999999999$abcdefghijklmnop$" + ("0" * 64)
    assert not verify_password("password", encoded)
    assert password_hash_needs_upgrade(encoded)


@pytest.mark.parametrize(
    "encoded",
    [
        "pbkdf2_sha256$600000$short$" + ("0" * 64),
        "pbkdf2_sha256$600000$abcdefghijklmnop$broken",
        "unknown$600000$abcdefghijklmnop$" + ("0" * 64),
        "x" * 513,
    ],
)
def test_damaged_password_hashes_require_upgrade(encoded: str) -> None:
    assert not verify_password("password", encoded)
    assert password_hash_needs_upgrade(encoded)


def test_token_helpers() -> None:
    token = "a" * 32
    assert token_hash(token) == "3ba3f5f43b92602683c19aee62a20342b084dd5971ddd33808d81a328879a547"
    assert utc_now().tzinfo == timezone.utc


def test_limiter_counts_only_accepted_events() -> None:
    now = [100.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0], cleanup_interval=5)

    assert limiter.allow("client", 2, 60)
    assert limiter.allow("client", 2, 60)
    assert not limiter.allow("client", 2, 60)
    now[0] += 61
    assert limiter.allow("client", 2, 60)


def test_limiter_evicts_inactive_keys() -> None:
    now = [100.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0], cleanup_interval=5)
    assert limiter.allow("old", 1, 10)
    now[0] += 11
    assert limiter.allow("new", 1, 10)
    assert limiter.tracked_keys() == 1


def test_limiter_is_atomic_under_contention() -> None:
    limiter = SlidingWindowLimiter()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: limiter.allow("shared", 5, 60), range(40)))
    assert sum(results) == 5


def test_limiter_rejects_window_changes_for_the_same_key() -> None:
    limiter = SlidingWindowLimiter()
    assert limiter.allow("client", 2, 60)
    with pytest.raises(ValueError, match="constant"):
        limiter.allow("client", 2, 30)
