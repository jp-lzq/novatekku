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
    assert len(sync_announced_lineup(db, LINEUP_RETAIL_PRICES)) == 12  # 18 Pro, 18 Pro Max, Duo × 4 capacities
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
    assert {(row["model"], row["capacity"]): row["retail_price"] for row in new_products} == {
        key: price for key, price in LINEUP_RETAIL_PRICES.items() if key[0].startswith("iPhone 18")
    }
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


def test_color_prices_separate_colour_quotes_from_all_colour_quotes(db, monkeypatch):
    from app.web.routers import prices as prices_router
    sync_announced_lineup(db, LINEUP_RETAIL_PRICES)
    product = db.query(Product).filter_by(model="iPhone 18 Pro", capacity="256").one()
    variants = {v.color_code: v for v in db.query(ProductVariant).filter_by(product_id=product.id)}
    good, other, flat, outlier = (Store(name=n, is_active=1) for n in ("Good", "Other", "Flat", "Outlier"))
    db.add_all([good, other, flat, outlier])
    db.flush()
    now = datetime.now(timezone.utc)
    for store, color, price in [(good, "black", 230000), (good, "silver", 228000), (other, "black", 231000), (outlier, "black", 400000)]:
        db.add(StoreProductPrice(store_id=store.id, product_id=product.id, product_variant_id=variants[color].id,
                                 source_type="official", price=price, collected_at=now))
    # "Flat" quotes one price for any colour
    db.add(StoreProductPrice(store_id=flat.id, product_id=product.id, product_variant_id=None,
                             source_type="official", price=233000, collected_at=now))
    db.commit()
    monkeypatch.setattr(prices_router, "_accepted_price_keys",
                        lambda _db, ids: {(product.id, s.id, 0) for s in (good, other, flat)})
    result = prices_router.get_color_prices(db)["products"]
    row = next(r for r in result if (r["model"], r["capacity"]) == ("iPhone 18 Pro", "256"))
    colors = {c["code"]: c for c in row["colors"]}
    assert (colors["black"]["price"], colors["black"]["store_count"]) == (231000, 2)
    assert (colors["silver"]["price"], colors["silver"]["store_count"]) == (228000, 1)
    assert colors["glacier"]["price"] is None and colors["glacier"]["store_count"] == 0
    assert row["all_colors"] == {"price": 233000, "store_count": 1}
    assert "store_id" not in str(result) and "Good" not in str(result)


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


def test_iphone_duo_has_its_own_colours_and_retail_prices(db):
    sync_announced_lineup(db, LINEUP_RETAIL_PRICES)
    duo = db.query(Product).filter_by(model="iPhone Duo").all()
    assert {(row.capacity, row.retail_price) for row in duo} == {("256", 364800), ("512", 399800), ("1TB", 469800), ("2TB", 574800)}
    variants = db.query(ProductVariant).join(Product).filter(Product.model == "iPhone Duo").all()
    assert len(variants) == 8
    assert {row.color_code for row in variants} == {"star-white", "night-sky"}
    assert {(row.color_name_ja, row.color_name_zh) for row in variants} == {("スターホワイト", "星光白色"), ("ナイトスカイ", "夜空色")}
    assert infer_color_code("iPhone Duo", "iPhone Duo 256GB Star White 未開封品") == "star-white"
    assert infer_color_code("iPhone Duo", "iPhone Duo 512GB ナイトスカイ") == "night-sky"
    assert infer_color_code("iPhone 18 Pro", "iPhone 18 Pro 256GB Star White") is None
