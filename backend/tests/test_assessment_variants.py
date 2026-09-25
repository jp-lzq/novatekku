from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.db.models import Product, ProductVariant, Store, StoreProductPrice
from app.web.routers.prices import _assessment_data, get_assessment_prices
from app.pricing.product_catalog import ensure_standard_variants


def test_assessment_uses_exact_color_and_default_store_price():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        product = Product(
            name="iPhone 17 Pro Max 256",
            model="iPhone 17 Pro Max",
            capacity="256",
            condition="新品",
        )
        colored_store = Store(name="カラー店", website_url="https://color.example", is_active=1)
        default_store = Store(name="共通価格店", website_url="https://default.example", is_active=1)
        db.add_all([product, colored_store, default_store])
        db.flush()
        variants = ensure_standard_variants(db)
        silver = variants[(product.id, "silver")]
        orange = variants[(product.id, "cosmic-orange")]
        now = datetime.now(timezone.utc)
        db.add_all([
            StoreProductPrice(
                store_id=colored_store.id,
                product_id=product.id,
                product_variant_id=silver.id,
                source_type="official",
                price=198000,
                collected_at=now,
            ),
            StoreProductPrice(
                store_id=colored_store.id,
                product_id=product.id,
                product_variant_id=orange.id,
                source_type="official",
                price=196000,
                collected_at=now,
            ),
            StoreProductPrice(
                store_id=default_store.id,
                product_id=product.id,
                product_variant_id=None,
                source_type="sheet",
                price=197000,
                collected_at=now,
            ),
        ])
        db.commit()

        private_data = _assessment_data(db)
        public_data = get_assessment_prices(db)
        assert set(public_data) == {"products"}
        assert len(public_data["products"]) == 1
        assert len(public_data["products"][0]["colors"]) == 3
        assert "jan_code" not in public_data["products"][0]["colors"][0]
        assert {row["id"] for row in private_data["stores"]} == {colored_store.id, default_store.id}
        colored_offers = [row for row in private_data["offers"] if row["store_id"] == colored_store.id]
        default_offers = [row for row in private_data["offers"] if row["store_id"] == default_store.id]
        assert {(row["variant_id"], row["price"]) for row in colored_offers} == {
            (silver.id, 198000),
            (orange.id, 196000),
        }
        assert len(default_offers) == 3
        assert {row["price"] for row in default_offers} == {197000}
        assert all(set(row) == {"store_id", "product_id", "variant_id", "price"} for row in private_data["offers"])
    finally:
        db.close()
