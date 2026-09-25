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
