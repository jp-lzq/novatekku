import json
from pathlib import Path


LINEUP = json.loads((Path(__file__).parents[1] / "data" / "iphone18.json").read_text(encoding="utf-8"))
LINEUP_RETAIL_PRICES = {
    (model["name"], capacity): price
    for model in LINEUP["models"]
    for capacity, price in model["retail_prices"].items()
}


def sync_announced_lineup(db, retail_prices):
    from app.db.models import Product
    from app.pricing.product_catalog import acquire_price_index_lock, ensure_standard_variants, normalize_capacity

    expected = set(LINEUP_RETAIL_PRICES)
    if set(retail_prices) != expected or any(type(price) is not int or price <= 0 for price in retail_prices.values()):
        raise ValueError("A complete verified Apple retail price set is required")

    acquire_price_index_lock(db)
    products = {
        (row.model, normalize_capacity(row.capacity)): row
        for row in db.query(Product).filter(
            Product.model.in_([model["name"] for model in LINEUP["models"]]),
            Product.condition == "新品",
        ).all()
        if not row.color
    }
    created = []
    for (model, capacity), price in retail_prices.items():
        if (model, capacity) in products:
            continue
        product = Product(
            name=f"{model} {capacity}", brand="Apple", model=model,
            capacity=capacity, color="", carrier="SIMフリー", condition="新品",
            retail_price=price,
        )
        db.add(product)
        created.append(product)
    db.flush()
    ensure_standard_variants(db, models={model["name"] for model in LINEUP["models"]})
    return created


def lineup_context():
    return json.dumps(LINEUP, ensure_ascii=False, separators=(",", ":"))
