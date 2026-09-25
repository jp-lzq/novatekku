from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session


CURRENT_PRICE_MAX_AGE_HOURS = 24


def current_price_cutoff(now: datetime | None = None) -> datetime:
    """現在価格として扱える最古の取得時刻を返す。"""
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return reference - timedelta(hours=CURRENT_PRICE_MAX_AGE_HOURS)


def refresh_current_best_flags(db: Session, product_id: int) -> None:
    """Mark only the latest observation per store, within 24 hours, as best."""
    from app.db.models import Price

    rows = (
        db.query(Price)
        .filter(Price.product_id == product_id, Price.scraped_at >= current_price_cutoff())
        .order_by(Price.scraped_at.desc(), Price.id.desc())
        .all()
    )
    latest_by_store: dict[int, Price] = {}
    for row in rows:
        latest_by_store.setdefault(row.store_id, row)
        row.is_best_price = 0
    if not latest_by_store:
        return

    best_price = max(row.price for row in latest_by_store.values())
    for row in latest_by_store.values():
        if row.price == best_price:
            row.is_best_price = 1
    db.flush()
