"""GET /api/v1/prices/where-to-sell: Japan, Hong Kong and the US ranked in yen with a recommendation."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import MarketPrice, MarketStore, MarketStorePrice, Price, PriceHistory, Product, Store
from app.db.session import Base, get_db
from app.pricing import current_prices
from app.web.routers import where_to_sell

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
JST = ZoneInfo("Asia/Tokyo")


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(where_to_sell.router, prefix="/api/v1")
app.dependency_overrides[get_db] = override_get_db
NOW = datetime.now(timezone.utc)
FX_UPDATED = "2026-11-27T09:00:00"


def set_rates(monkeypatch, usd=150.0, hkd=20.0):
    rates = {code: {"rate": rate} for code, rate in (("USD", usd), ("HKD", hkd)) if rate}
    monkeypatch.setattr(where_to_sell, "get_cached_fx_rates", lambda: {"rates": rates, "last_updated": FX_UPDATED})


@pytest.fixture(autouse=True)
def seed(monkeypatch):
    set_rates(monkeypatch)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    p256 = Product(name="iPhone 17 Pro 256GB", model="iPhone 17 Pro", capacity="256GB", retail_price=179800)
    p512 = Product(name="iPhone 17 Pro 512", model="iPhone 17 Pro", capacity="512", retail_price=214800)
    used = Product(name="iPhone 17 Pro 256 used", model="iPhone 17 Pro", capacity="256", condition="中古A", retail_price=179800)
    other = Product(name="iPhone 17 256", model="iPhone 17", capacity="256", retail_price=129800)
    stores = {name: Store(name=name) for name in ("店A", "店B", "店C", "外れ店")}
    stores["閉店"] = Store(name="閉店", is_active=0)
    db.add_all([p256, p512, used, other, *stores.values()])
    db.flush()

    def japan(store, product, value, hours_ago=1):
        db.add(Price(product_id=product.id, store_id=stores[store].id, price=value, scraped_at=NOW - timedelta(hours=hours_ago)))

    japan("店A", p256, 200000)
    japan("店B", p256, 199000)
    japan("店C", p256, 198000)
    japan("外れ店", p256, 260000)  # far above the others: dropped as an outlier
    japan("閉店", p256, 205000)  # inactive store
    japan("店A", used, 250000)  # used phone: not compared with new overseas prices
    japan("店B", p256, 230000, hours_ago=30)  # older than 24 hours
    japan("店A", p512, 230000)

    def snapshot(market, capacity, value, currency, hours_ago=1, color=None, offers=1, source="feed-alpha"):
        db.add(MarketPrice(market=market, source=source, model="iPhone 17 Pro", capacity=capacity, color_code=color,
                           price=value, currency=currency, offers=offers, collected_at=NOW - timedelta(hours=hours_ago)))

    snapshot("us", "256", 1300, "USD", offers=4)
    snapshot("us", "256", 2000, "USD", hours_ago=60, source="feed-beta")  # older than 48 hours
    snapshot("hk", "256", 9900, "HKD", color="silver", offers=3)
    snapshot("hk", "256", 9800, "HKD", color="deep-blue", offers=2)
    snapshot("us", "1TB", 1600, "USD")  # no Japanese price for 1TB

    surgeon = MarketStore(market="us", name="Buyback Surgeon", currency="USD")
    locked = MarketStore(market="us", name="Sell Locked", currency="USD")
    db.add_all([surgeon, locked])
    db.flush()
    for store, value in ((surgeon, 1300), (locked, 1280)):
        db.add(MarketStorePrice(collected_at=NOW - timedelta(hours=2), market_store_id=store.id, product_id=p256.id,
                                price=value, currency="USD", source="t"))
    db.commit()
    db.close()


def get(params):
    return TestClient(app).get("/api/v1/prices/where-to-sell", params=params)


def body(**params):
    response = get({"model": "iPhone 17 Pro", "capacity": "256", **params})
    assert response.status_code == 200, response.text
    return response.json()


def by_market(result):
    return {entry["market"]: entry for entry in result["markets"]}


def test_markets_ranked_in_yen_and_japan_best():
    result = body()
    assert [entry["market"] for entry in result["markets"]] == ["jp", "hk", "us"]
    markets = by_market(result)
    assert (markets["jp"]["price"], markets["jp"]["currency"], markets["jp"]["store"]) == (200000, "JPY", "店A")
    assert (markets["hk"]["price"], markets["hk"]["currency"], markets["hk"]["price_jpy"]) == (9900, "HKD", 198000)
    assert (markets["us"]["price"], markets["us"]["price_jpy"], markets["us"]["store"]) == (1300, 195000, "Buyback Surgeon")
    assert [entry["rank"] for entry in result["markets"]] == [1, 2, 3]
    assert markets["us"]["behind_top"] == 5000
    assert result["advice"] == "japan_best" and result["best_market"] == "jp"
    assert (result["best_overseas_market"], result["overseas_gap"], result["overseas_gap_percent"]) == ("hk", -2000, -1.0)
    assert result["small_gap_percent"] == 5.0


def test_japan_uses_only_accepted_current_new_device_prices():
    stores = by_market(body())["jp"]["stores"]
    assert [(item["store"], item["price"]) for item in stores] == [("店A", 200000), ("店B", 199000), ("店C", 198000)]
    assert all(item["currency"] == "JPY" and item["price_jpy"] == item["price"] for item in stores)


def test_restricted_stores_are_not_used(monkeypatch):
    monkeypatch.setattr(current_prices, "PUBLIC_PRICE_RESTRICTED_STORES", frozenset({"店A"}))
    markets = by_market(body())
    assert (markets["jp"]["price"], markets["jp"]["store"]) == (199000, "店B")
    assert "店A" not in [item["store"] for item in markets["jp"]["stores"]]


def test_overseas_stores_and_buyers():
    markets = by_market(body())
    assert [(item["store"], item["price"], item["price_jpy"]) for item in markets["us"]["stores"]] == [
        ("Buyback Surgeon", 1300, 195000), ("Sell Locked", 1280, 192000)]
    assert markets["us"]["buyers"] == 4 and markets["hk"]["buyers"] == 5
    assert markets["hk"]["stores"] == []  # Hong Kong shops are not named


def test_small_overseas_lead(monkeypatch):
    set_rates(monkeypatch, usd=160.0)  # 1300 USD = 208,000 yen, 4 % above Japan
    result = body()
    assert result["advice"] == "overseas_small" and result["best_market"] == "us"
    assert (result["overseas_gap"], result["overseas_gap_percent"]) == (8000, 4.0)
    assert by_market(result)["jp"]["rank"] == 2


def test_clear_overseas_lead(monkeypatch):
    set_rates(monkeypatch, usd=170.0)  # 221,000 yen, 10.5 % above Japan
    result = body()
    assert result["advice"] == "overseas_clear"
    assert (result["overseas_gap"], result["overseas_gap_percent"]) == (21000, 10.5)


def test_without_exchange_rates_only_japan_is_ranked(monkeypatch):
    set_rates(monkeypatch, usd=None, hkd=None)
    result = body()
    assert [entry["market"] for entry in result["markets"]] == ["jp"]
    assert result["advice"] == "japan_only" and result["overseas_gap"] is None
    assert result["fx"]["rates"] == {"HKD": None, "USD": None}


def test_capacity_spellings_and_default():
    assert body(capacity="256GB")["markets"] == body(capacity="256")["markets"]
    default = get({"model": "iPhone 17 Pro"}).json()
    assert default["capacity"] == "256" and default["capacities"] == ["256", "512", "1TB"]
    one_tb = body(capacity="1024")
    assert one_tb["capacity"] == "1TB"


def test_capacity_without_any_price_is_empty():
    result = body(capacity="2TB")
    assert result["capacity"] == "2TB" and result["markets"] == [] and result["advice"] is None
    assert result["capacities"] == ["256", "512", "1TB"]


def test_japan_without_overseas_price():
    result = body(capacity="512")
    assert [entry["market"] for entry in result["markets"]] == ["jp"]
    assert result["advice"] == "japan_only"


def test_overseas_without_japanese_price_has_no_advice():
    result = body(capacity="1TB")
    assert [(entry["market"], entry["price_jpy"], entry["rank"]) for entry in result["markets"]] == [("us", 240000, 1)]
    assert result["advice"] is None and result["best_market"] == "us"


def test_unknown_model_and_bad_input():
    assert get({"model": "iPhone 99"}).status_code == 404
    assert get({"model": "iPhone 17 Pro", "capacity": "huge"}).status_code == 422
    assert get({}).status_code == 422
    assert get({"model": "x" * 101}).status_code == 422


def test_model_known_without_prices_is_empty():
    result = get({"model": "iPhone 17"}).json()
    assert result["capacities"] == [] and result["capacity"] is None and result["markets"] == []


def test_japan_direction_from_price_history():
    db = Session()
    product = db.query(Product).filter(Product.capacity == "256GB").one()
    store_ids = [store.id for store in db.query(Store).filter(Store.name.in_(["店A", "店B", "店C"])).order_by(Store.name)]
    today = datetime.now(JST).date()
    for days_ago, prices in ((10, (220000, 219000, 218000)), (0, (200000, 199000, 198000))):
        when = datetime.combine(today - timedelta(days=days_ago), time(0, 30))  # naive = Japan time
        for store_id, value in zip(store_ids, prices):
            db.add(PriceHistory(product_id=product.id, store_id=store_id, price=value, recorded_at=when))
    db.commit()
    db.close()
    result = body()
    assert result["japan_direction"] == "down"
    assert result["japan_change_7d"]["change"] == -20000 and result["japan_change_7d"]["percent"] == -9.1


def test_direction_unknown_without_history():
    result = body()
    assert result["japan_direction"] is None and result["japan_change_7d"] is None


def test_times_rates_and_no_source_names():
    response = get({"model": "iPhone 17 Pro", "capacity": "256"})
    result = response.json()
    assert result["fx"] == {"rates": {"HKD": 20.0, "USD": 150.0}, "updated_at": FX_UPDATED}
    assert all(result["updated_at"][market] for market in ("jp", "hk", "us"))
    assert "feed-alpha" not in response.text and "feed-beta" not in response.text


def test_answers_are_cached_for_a_minute():
    first = body()
    db = Session()
    db.query(Price).delete()
    db.commit()
    db.close()
    assert body() == first
    where_to_sell.PUBLIC_PRICE_CACHE.clear()
    assert body()["markets"][0]["market"] == "hk"
