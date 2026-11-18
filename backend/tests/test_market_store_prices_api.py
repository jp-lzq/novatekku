"""GET /api/v1/prices/market-stores: overseas prices per store, best first."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import MarketStore, MarketStorePrice, Product, ProductVariant
from app.db.session import Base, get_db
from app.web.routers import prices

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(prices.router, prefix="/api/v1")
app.dependency_overrides[get_db] = override_get_db
NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    p256 = Product(name="iPhone 17 Pro 256", model="iPhone 17 Pro", capacity="256")
    p1tb = Product(name="iPhone 17 Pro 1TB", model="iPhone 17 Pro", capacity="1TB")
    db.add_all([p256, p1tb])
    db.flush()
    silver = ProductVariant(product_id=p256.id, color_code="silver", color_name_ja="シルバー", color_name_en="Silver", color_name_zh="银色")
    blue = ProductVariant(product_id=p256.id, color_code="deep-blue", color_name_ja="ディープブルー", color_name_en="Deep Blue", color_name_zh="深蓝色")
    surgeon = MarketStore(market="us", name="Buyback Surgeon", currency="USD")
    locked = MarketStore(market="us", name="Sell Locked", currency="USD")
    closed = MarketStore(market="us", name="Closed Buyer", currency="USD", is_active=False)
    hong_kong = MarketStore(market="hk", name="香港", currency="HKD")
    db.add_all([silver, blue, surgeon, locked, closed, hong_kong])
    db.flush()

    def price(store, product, value, hours_ago=1, variant=None, currency="USD"):
        db.add(MarketStorePrice(collected_at=NOW - timedelta(hours=hours_ago), market_store_id=store.id, product_id=product.id,
                                product_variant_id=variant.id if variant else None, price=value, currency=currency, source="t"))

    price(surgeon, p256, 771)
    price(surgeon, p256, 700, hours_ago=20)  # older price of the same store: not shown
    price(locked, p256, 770)
    price(locked, p1tb, 900)
    price(surgeon, p1tb, 950, hours_ago=60)  # older than 48 hours: not shown
    price(closed, p256, 999)  # inactive store: not shown
    price(hong_kong, p256, 9000, variant=silver, currency="HKD")
    price(hong_kong, p256, 9100, variant=blue, currency="HKD")
    db.commit()
    db.close()


def get(market):
    return TestClient(app).get("/api/v1/prices/market-stores", params={"market": market}).json()


def test_us_stores_best_first_with_their_latest_price():
    body = get("us")
    assert body["market"] == "us" and body["currency"] == "USD" and body["updated_at"]
    products = {(p["model"], p["capacity"]): p for p in body["products"]}
    assert [(s["store"], s["price"]) for s in products[("iPhone 17 Pro", "256")]["stores"]] == [("Buyback Surgeon", 771), ("Sell Locked", 770)]
    assert [(s["store"], s["price"]) for s in products[("iPhone 17 Pro", "1TB")]["stores"]] == [("Sell Locked", 900)]
    assert products[("iPhone 17 Pro", "256")]["color_code"] is None
    assert all("collected_at" in store for p in body["products"] for store in p["stores"])


def test_capacities_are_in_size_order():
    assert [p["capacity"] for p in get("us")["products"]] == ["256", "1TB"]


def test_hong_kong_is_one_store_per_colour():
    body = get("hk")
    assert body["currency"] == "HKD"
    assert [(p["color_code"], [s["store"] for s in p["stores"]], p["stores"][0]["price"]) for p in body["products"]] == [
        ("deep-blue", ["香港"], 9100), ("silver", ["香港"], 9000)]


def test_markets_do_not_mix_and_input_is_validated():
    assert all(s["store"] != "香港" for p in get("us")["products"] for s in p["stores"])
    assert TestClient(app).get("/api/v1/prices/market-stores", params={"market": "jp"}).status_code == 422


def test_empty_market():
    db = Session()
    db.query(MarketStorePrice).delete()
    db.commit()
    db.close()
    assert get("us") == {"market": "us", "currency": "USD", "updated_at": None, "products": []}
