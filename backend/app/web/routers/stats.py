from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import DailyHighPrice, Price, PriceHistory, Product, Store
from app.pricing.current_prices import latest_prices_query
from app.web.routers.common import price_to_dict
from app.web.routers.members import AuthContext, require_admin
from app.pricing.fx_rates import get_fx_rates

router = APIRouter()


# Stats
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    total_products = db.query(func.count(Product.id)).scalar()
    total_stores = db.query(func.count(Store.id)).filter(Store.is_active == 1).scalar()

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_updates = db.query(func.count(Price.id)).filter(Price.scraped_at >= today).scalar()

    since_24h = datetime.now() - timedelta(hours=24)
    price_changes_24h = db.query(func.count(Price.id)).filter(
        Price.scraped_at >= since_24h,
        Price.price_change != 0
    ).scalar()

    # 最新の更新時刻を取得
    latest_price = db.query(Price).order_by(desc(Price.scraped_at)).first()
    last_updated = latest_price.scraped_at.isoformat() if latest_price and latest_price.scraped_at else None

    return {
        "total_products": total_products or 0,
        "total_stores": total_stores or 0,
        "today_updates": today_updates or 0,
        "price_changes_24h": price_changes_24h or 0,
        "last_updated": last_updated
    }

@router.get("/homepage/summary")
def get_homepage_summary(
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta

    latest_prices = latest_prices_query(db).all()
    best_by_product = {}

    for price in latest_prices:
        if price.profit is None:
            continue

        current = best_by_product.get(price.product_id)
        if current is None:
            best_by_product[price.product_id] = price
            continue

        current_profit = current.profit if current.profit is not None else float("-inf")
        next_profit = price.profit if price.profit is not None else float("-inf")
        if next_profit > current_profit or (
            next_profit == current_profit and price.price > current.price
        ):
            best_by_product[price.product_id] = price

    recommended_models = sorted(
        best_by_product.values(),
        key=lambda item: (
            item.profit if item.profit is not None else float("-inf"),
            item.price,
        ),
        reverse=True,
    )[:3]

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_24h = now - timedelta(hours=24)

    latest_update = None
    if latest_prices:
        latest_update = max(
            (price.scraped_at for price in latest_prices if price.scraped_at),
            default=None,
        )
    oldest_price = db.query(Price).order_by(Price.scraped_at.asc()).first()
    newest_price = db.query(Price).order_by(desc(Price.scraped_at)).first()
    covered_days = db.query(func.count(func.distinct(func.date(Price.scraped_at)))).scalar() or 0

    return {
        "recommended_models": [price_to_dict(price) for price in recommended_models],
        "stats": {
            "last_updated": latest_update.isoformat() if latest_update else None,
            "first_collected_at": oldest_price.scraped_at.isoformat() if oldest_price and oldest_price.scraped_at else None,
            "latest_collected_at": newest_price.scraped_at.isoformat() if newest_price and newest_price.scraped_at else None,
            "today_updates": db.query(func.count(Price.id)).filter(Price.scraped_at >= today).scalar() or 0,
            "total_products": db.query(func.count(Product.id)).scalar() or 0,
            "total_stores": db.query(func.count(Store.id)).filter(Store.is_active == 1).scalar() or 0,
            "total_price_records": db.query(func.count(Price.id)).scalar() or 0,
            "latest_price_records": len(latest_prices),
            "total_history_records": db.query(func.count(PriceHistory.id)).scalar() or 0,
            "total_daily_high_records": db.query(func.count(DailyHighPrice.id)).scalar() or 0,
            "covered_days": covered_days,
            "price_changes_24h": db.query(func.count(Price.id)).filter(
                Price.scraped_at >= since_24h,
                Price.price_change != 0,
            ).scalar() or 0,
        },
    }

@router.get("/fx")
def get_fx_rates_endpoint():
    return get_fx_rates()
