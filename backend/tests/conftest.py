import pytest

from app.ai_gateway.evidence.loaders import PAST_DAYS_CACHE
from app.infrastructure.ttl_cache import PUBLIC_PRICE_CACHE


@pytest.fixture(autouse=True)
def clear_public_price_cache():
    """Each test sees its own database, so cached answers must not leak between tests."""
    PUBLIC_PRICE_CACHE.clear()
    PAST_DAYS_CACHE.clear()
    yield
    PUBLIC_PRICE_CACHE.clear()
    PAST_DAYS_CACHE.clear()
