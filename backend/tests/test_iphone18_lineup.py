from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.models import Product, ProductVariant, Price, Store, StoreProductPrice
from app.web.routers.prices import _assessment_data, get_assessment_prices
from app.pricing.iphone_lineup import LINEUP_RETAIL_PRICES, sync_announced_lineup
from app.pricing.product_catalog import infer_color_code


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def test_lineup_is_additive_and_idempotent(db):
    old = Product(name="iPhone 17 Pro 256", model="iPhone 17 Pro", capacity="256", retail_price=194800)
    db.add(old)
    db.commit()
    old_values = (old.id, old.created_at, old.updated_at, old.retail_price)
    assert len(sync_announced_lineup(db, LINEUP_RETAIL_PRICES)) == 8
    db.commit()
    assert sync_announced_lineup(db, LINEUP_RETAIL_PRICES) == []
    db.commit()
    rows = db.query(ProductVariant).join(Product).filter(Product.model.like("iPhone 18%")).all()
    assert len(rows) == 32
    assert all(row.jan_code is None for row in rows)
    assert all(row.color_name_ja and row.color_name_en and row.color_name_zh for row in rows)
    assert (old.id, old.created_at, old.updated_at, old.retail_price) == old_values
    assert db.query(Price).count() == 0
    data = _assessment_data(db)
    assert len([row for row in data["products"] if row["model"].startswith("iPhone 18")]) == 8
    assert data["offers"] == []
    catalog = get_assessment_prices(db)["products"]
    new_products = [row for row in catalog if row["model"].startswith("iPhone 18")]
    assert len(new_products) == 8
    assert {(row["model"], row["capacity"]): row["retail_price"] for row in new_products} == LINEUP_RETAIL_PRICES
    for row in new_products:
        assert set(row) == {"id", "name", "model", "capacity", "retail_price", "carrier", "colors"}
        assert row["carrier"] == "SIMフリー"
        assert "price" not in row
        assert len(row["colors"]) == 4


def test_incomplete_lineup_cannot_write_products(db):
    with pytest.raises(ValueError):
        sync_announced_lineup(db, {("iPhone 18 Pro", "256"): 219800})
    assert db.query(Product).count() == 0


@pytest.mark.parametrize("color,code", [
    ("グレイシャー", "glacier"), ("Glacier", "glacier"), ("冰川蓝色", "glacier"),
    ("バーガンディ", "burgundy"), ("Burgundy", "burgundy"), ("勃艮第酒红色", "burgundy"),
])
def test_new_colors(color, code):
    assert infer_color_code("iPhone 18 Pro Max", color) == code
    assert infer_color_code("iPhone 17 Pro Max", color) is None



def test_new_products_keep_color_fallback_and_24_hour_expiry(db):
    sync_announced_lineup(db, LINEUP_RETAIL_PRICES)
    product = db.query(Product).filter_by(model="iPhone 18 Pro", capacity="256").one()
    store = Store(name="Test store", is_active=1)
    db.add(store)
    db.flush()
    quote = StoreProductPrice(store_id=store.id, product_id=product.id, source_type="sheet", price=230000,
                              collected_at=datetime.now(timezone.utc) - timedelta(hours=25))
    db.add(quote)
    db.commit()
    assert _assessment_data(db)["offers"] == []
    quote.collected_at = datetime.now(timezone.utc)
    db.commit()
    offers = _assessment_data(db)["offers"]
    assert len(offers) == 4
    assert {row["price"] for row in offers} == {230000}


def test_color_prices_use_accepted_stores_and_hide_store_names(db, monkeypatch):
    from app.web.routers import prices as prices_router
    sync_announced_lineup(db, LINEUP_RETAIL_PRICES)
    product = db.query(Product).filter_by(model="iPhone 18 Pro", capacity="256").one()
    variants = {v.color_code: v for v in db.query(ProductVariant).filter_by(product_id=product.id)}
    good, other, outlier = Store(name="Good", is_active=1), Store(name="Other", is_active=1), Store(name="Outlier", is_active=1)
    db.add_all([good, other, outlier])
    db.flush()
    now = datetime.now(timezone.utc)
    rows = [(good, "black", 230000), (good, "silver", 228000), (other, "black", 231000), (outlier, "black", 400000)]
    for store, color, price in rows:
        db.add(StoreProductPrice(store_id=store.id, product_id=product.id, product_variant_id=variants[color].id,
                                 source_type="official", price=price, collected_at=now))
    db.commit()
    monkeypatch.setattr(prices_router, "_accepted_price_keys",
                        lambda _db, ids: {(product.id, good.id, 0), (product.id, other.id, 0)})
    result = prices_router.get_color_prices(db)["products"]
    assert len(result) == 1
    row = result[0]
    assert (row["model"], row["capacity"]) == ("iPhone 18 Pro", "256")
    colors = {c["code"]: c for c in row["colors"]}
    assert colors["black"]["price"] == 231000 and colors["black"]["store_count"] == 2
    assert colors["silver"]["price"] == 228000 and colors["silver"]["store_count"] == 1
    assert "glacier" not in colors
    assert "store" not in str(result).replace("store_count", "")


def test_market_prices_take_best_price_and_count_buyers(db):
    from app.db.models import MarketPrice
    from app.web.routers import prices as prices_router
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=3)
    rows = [
        # two Hong Kong sources, latest snapshot of each
        ("iphonepricehk", now, "black", 11800, 11299, 1),
        ("debitbaba", now, "black", 11840, None, 1),
        ("debitbaba", now, "silver", 11750, None, 1),
        ("iphonepricehk", old, "black", 99999, 11299, 1),  # older snapshot is ignored
    ]
    for source, at, color, price, official, offers in rows:
        db.add(MarketPrice(market="hk", source=source, model="iPhone 18 Pro Max", capacity="256", color_code=color,
                           price=price, currency="HKD", official_price=official, offers=offers, collected_at=at))
    db.add(MarketPrice(market="us", source="bankmycell", model="iPhone 18 Pro Max", capacity="256", color_code=None,
                       price=1070, currency="USD", offers=9, collected_at=now))
    db.add(MarketPrice(market="hk", source="stale", model="iPhone 18 Pro Max", capacity="256", color_code="black",
                       price=50000, currency="HKD", collected_at=now - timedelta(days=3)))
    db.commit()

    hk = prices_router.get_market_prices("hk", db)
    assert hk["currency"] == "HKD"
    product = hk["products"][0]
    assert (product["model"], product["capacity"], product["official_price"]) == ("iPhone 18 Pro Max", "256", 11299)
    colors = {c["code"]: c for c in product["colors"]}
    assert colors["black"] == {"code": "black", "price": 11840, "store_count": 2}
    assert colors["silver"] == {"code": "silver", "price": 11750, "store_count": 1}

    us = prices_router.get_market_prices("us", db)
    assert us["products"][0]["colors"] == [{"code": None, "price": 1070, "store_count": 9}]
