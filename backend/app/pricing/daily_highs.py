from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DailyHighPrice, Price


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def refresh_daily_high_for_product(db: Session, product_id: int, target_date=None, commit: bool = True) -> int:
    day = _as_date(target_date or datetime.now())
    prices = (
        db.query(Price)
        .filter(
            Price.product_id == product_id,
            func.date(Price.scraped_at) == day,
        )
        .order_by(Price.scraped_at.asc(), Price.id.asc())
        .all()
    )
    if not prices:
        return 0

    price_values = [price.price for price in prices]
    high_price = max(price_values)
    best_price = next(price for price in reversed(prices) if price.price == high_price)

    daily_high = (
        db.query(DailyHighPrice)
        .filter(
            DailyHighPrice.product_id == product_id,
            DailyHighPrice.date == day,
        )
        .first()
    )
    if not daily_high:
        daily_high = DailyHighPrice(product_id=product_id, date=day)
        db.add(daily_high)

    daily_high.open_price = prices[0].price
    daily_high.high_price = high_price
    daily_high.low_price = min(price_values)
    daily_high.close_price = prices[-1].price
    daily_high.best_store_name = best_price.store.name if best_price.store else None

    if commit:
        db.commit()

    return 1


def refresh_daily_highs_for_product(db: Session, product_id: int, days: int = 90, commit: bool = True) -> int:
    since = datetime.now() - timedelta(days=days)
    dates = (
        db.query(func.date(Price.scraped_at).label("date"))
        .filter(
            Price.product_id == product_id,
            Price.scraped_at >= since,
        )
        .group_by(func.date(Price.scraped_at))
        .order_by(func.date(Price.scraped_at))
        .all()
    )

    updated = 0
    for row in dates:
        updated += refresh_daily_high_for_product(db, product_id, row.date, commit=False)

    if commit:
        db.commit()

    return updated


def refresh_daily_highs_for_products(db: Session, product_ids: list[int], days: int = 90) -> int:
    updated = 0
    for product_id in product_ids:
        updated += refresh_daily_highs_for_product(db, product_id, days=days, commit=False)
    db.commit()
    return updated
