"""Price API: short public cache, 404 for unknown products, current store count."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import MarketPrice, Price, PriceHistory, Product, Store
from app.db.session import Base, get_db
from app.infrastructure.ttl_cache import PUBLIC_PRICE_CACHE, TTLCache
from app.web.routers import prices

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(prices.router, prefix="/api/v1")
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def seed_prices(values=(200000, 199000, 198000)):
    db = TestingSessionLocal()
    product = Product(name="iPhone 17 Pro 256", model="iPhone 17 Pro", capacity="256", retail_price=219800)
    stores = [Store(name=f"店{index}") for index in range(len(values))]
    db.add(product)
    db.add_all(stores)
    db.commit()
    now = datetime.now(timezone.utc)
    for store, value in zip(stores, values):
        db.add(Price(product_id=product.id, store_id=store.id, price=value, scraped_at=now))
    db.commit()
    product_id = product.id
    db.close()
    return product_id


# ---------------------------------------------------------------------------
# TTLCache
# ---------------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_cache_returns_the_stored_value_until_it_expires():
    clock = FakeClock()
    cache = TTLCache(ttl_seconds=60, clock=clock)
    calls = []
    compute = lambda: calls.append(1) or len(calls)  # noqa: E731
    assert cache.get_or_set("k", compute) == 1
    clock.now += 59
    assert cache.get_or_set("k", compute) == 1
    clock.now += 2
    assert cache.get_or_set("k", compute) == 2
    assert (cache.hits, cache.misses) == (1, 2)


def test_cache_keys_are_independent_and_size_is_bounded():
    cache = TTLCache(ttl_seconds=60, max_entries=2, clock=FakeClock())
    for key in ("a", "b", "c"):
        cache.get_or_set(key, lambda key=key: key)
    assert len(cache) == 2
    assert cache.get_or_set("a", lambda: "recomputed") == "recomputed"  # "a" was evicted first


def test_cache_does_not_store_failures():
    cache = TTLCache(clock=FakeClock())

    def broken():
        raise RuntimeError("database down")

    with pytest.raises(RuntimeError):
        cache.get_or_set("k", broken)
    assert cache.get_or_set("k", lambda: "ok") == "ok"


def test_clear_empties_the_cache():
    cache = TTLCache(clock=FakeClock())
    cache.get_or_set("k", lambda: 1)
    cache.clear()
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

def test_price_list_is_cached_per_filter(client):
    product_id = seed_prices()
    first = client.get("/api/v1/prices").json()
    assert [row["price"] for row in first] == [200000, 199000, 198000]

    db = TestingSessionLocal()
    db.query(Price).delete()
    db.commit()
    db.close()

    assert client.get("/api/v1/prices").json() == first  # served from the cache
    assert client.get("/api/v1/prices", params={"product_id": product_id}).json() == []  # different key
    PUBLIC_PRICE_CACHE.clear()
    assert client.get("/api/v1/prices").json() == []


def test_limit_applies_after_the_cache(client):
    seed_prices()
    assert len(client.get("/api/v1/prices", params={"limit": 2}).json()) == 2
    assert len(client.get("/api/v1/prices").json()) == 3


def test_market_prices_are_cached_per_market(client):
    db = TestingSessionLocal()
    db.add(MarketPrice(market="hk", source="debitbaba", model="iPhone 17 Pro", capacity="256", color_code="silver",
                       price=10000, currency="HKD", collected_at=datetime.now(timezone.utc)))
    db.commit()
    db.close()
    hk = client.get("/api/v1/prices/markets", params={"market": "hk"}).json()
    us = client.get("/api/v1/prices/markets", params={"market": "us"}).json()
    assert hk["products"][0]["colors"][0]["price"] == 10000
    assert us["products"] == []
    assert ("markets", "hk") in PUBLIC_PRICE_CACHE._entries and ("markets", "us") in PUBLIC_PRICE_CACHE._entries


def test_latest_prices_for_unknown_product_is_404(client):
    response = client.get("/api/v1/prices/latest/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_latest_prices_for_known_product_without_prices_is_empty(client):
    product_id = seed_prices(values=())
    assert client.get(f"/api/v1/prices/latest/{product_id}").json() == []


def test_kline_summary_reports_current_store_count(client):
    """A store with one point in the period has no chart line but is still quoting today."""
    db = TestingSessionLocal()
    product = Product(name="iPhone Duo 256", model="iPhone Duo", capacity="256", retail_price=364800)
    old_store, new_store = Store(name="長く掲載"), Store(name="今日から掲載")
    db.add_all([product, old_store, new_store])
    db.commit()
    today = datetime.now(timezone.utc).replace(hour=1, minute=0, second=0, microsecond=0)
    db.add(PriceHistory(product_id=product.id, store_id=old_store.id, price=400000, recorded_at=today - timedelta(days=1)))
    db.add(PriceHistory(product_id=product.id, store_id=old_store.id, price=401000, recorded_at=today))
    db.add(PriceHistory(product_id=product.id, store_id=new_store.id, price=383000, recorded_at=today + timedelta(minutes=5)))
    db.commit()
    product_id = product.id
    db.close()

    summary = client.get(f"/api/v1/prices/kline-advanced/{product_id}?interval=1d&days=7").json()["summary"]
    assert summary["store_count"] == 1  # only the long-listed store draws a line
    assert summary["latest_store_count"] == 2  # both stores quote today


def test_kline_summary_without_history(client):
    product_id = seed_prices(values=())
    summary = client.get(f"/api/v1/prices/kline-advanced/{product_id}").json()["summary"]
    assert summary["latest_store_count"] == 0
