from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.db.models import PriceHistory, Product, Store
from app.web.routers import prices
from app.pricing.price_consensus import consensus_bounds, partition_consensus


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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


def test_consensus_filter_rejects_the_176000_store_quote():
    values = [194000, 193500, 193000, 193000, 190000, 186000, 184000, 176000]

    accepted, rejected, details = partition_consensus(values, lambda value: value)

    assert 176000 in rejected
    assert 193000 in accepted
    assert details["lower_bound"] > 176000


def test_current_yamada_quote_remains_inside_consensus():
    values = [196000, 193500, 193000, 192500, 191000, 190000, 189000, 188100]
    _, lower_bound, upper_bound = consensus_bounds(values)

    assert lower_bound <= 188100 <= upper_bound


def test_advanced_kline_uses_valid_stores_and_returns_average_line(client):
    db = TestingSessionLocal()
    product = Product(name="iPhone 17 Pro Max 256", model="iPhone 17 Pro Max", capacity="256", retail_price=194800)
    stores = [
        Store(name="森森買取"),
        Store(name="買取ルデヤ"),
        Store(name="買取ホムラ"),
        Store(name="アキモバ"),
        Store(name="ヤマダ電機"),
    ]
    db.add(product)
    db.add_all(stores)
    db.commit()
    db.refresh(product)
    product_id = product.id
    for store in stores:
        db.refresh(store)

    now = datetime.now(timezone.utc).replace(hour=1, minute=0, second=0, microsecond=0)
    for days_ago in (1, 0):
        recorded_at = now - timedelta(days=days_ago)
        for offset, (store, value) in enumerate(zip(stores, [194000, 193000, 191000, 176000, 250000])):
            db.add(PriceHistory(
                product_id=product.id,
                store_id=store.id,
                price=value,
                recorded_at=recorded_at + timedelta(minutes=offset),
            ))
    db.commit()
    db.close()

    response = client.get(f"/api/v1/prices/kline-advanced/{product_id}?interval=1d&days=7")

    assert response.status_code == 200
    data = response.json()
    assert len(data["candles"]) == 2
    assert all(candle["low"] == 191000 for candle in data["candles"])
    assert all(candle["average"] == 192700 for candle in data["candles"])
    assert all(candle["filtered_store_count"] == 2 for candle in data["candles"])
    assert [point["value"] for point in data["average_series"]] == [192700, 192700]
    assert "ヤマダ電機" not in [series["store_name"] for series in data["store_series"]]
    assert data["summary"]["latest_average"] == 192700
    assert data["summary"]["store_count"] == 3
    assert data["summary"]["filtered_store_points"] == 4
