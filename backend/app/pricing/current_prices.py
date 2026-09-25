"""Queries for the current public price set."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Price, Product, Store
from app.pricing.price_validity import current_price_cutoff
from app.pricing.source_policy import PUBLIC_PRICE_RESTRICTED_STORES


def latest_prices_query(db: Session, *, now: datetime | None = None):
    cutoff = current_price_cutoff(now)
    subquery = db.query(
        Price.product_id,
        Price.store_id,
        func.max(Price.scraped_at).label("max_scraped_at"),
    ).filter(
        Price.scraped_at >= cutoff,
    ).group_by(Price.product_id, Price.store_id).subquery()

    return db.query(Price).join(
        subquery,
        (Price.product_id == subquery.c.product_id)
        & (Price.store_id == subquery.c.store_id)
        & (Price.scraped_at == subquery.c.max_scraped_at),
    ).join(Store).join(Product).filter(
        Price.scraped_at >= cutoff,
        Store.name.notin_(PUBLIC_PRICE_RESTRICTED_STORES),
    )
