import pytest

from app.infrastructure.ttl_cache import PUBLIC_PRICE_CACHE


@pytest.fixture(autouse=True)
def clear_public_price_cache():
    """Each test sees its own database, so cached answers must not leak between tests."""
    PUBLIC_PRICE_CACHE.clear()
    yield
    PUBLIC_PRICE_CACHE.clear()
