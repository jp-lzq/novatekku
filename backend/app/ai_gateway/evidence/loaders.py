"""Database reads for the price evidence: daily best prices and overseas snapshots."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import MarketPrice, PriceHistory, Product, Store
from app.infrastructure.ttl_cache import TTLCache
from app.pricing.market_average import _price_ceiling
from app.pricing.price_consensus import DEFAULT_MIN_STORE_COUNT, partition_consensus
from app.pricing.source_policy import PUBLIC_PRICE_RESTRICTED_STORES

from .matching import normalise_capacity

TREND_DAYS = 35
MAX_TREND_KEYS = 12  # model/capacity pairs per question that get a trend (keeps the query small)
VALID_PRICE_FLOOR = 10000  # same floor as the K-line chart
MARKET_MAX_AGE_HOURS = 48  # same freshness rule as /api/v1/prices/markets
JST = ZoneInfo("Asia/Tokyo")

# Finished days never change, so their daily best is computed once and kept;
# only today is read again on every question.
PAST_DAYS_CACHE = TTLCache(ttl_seconds=6 * 3600, max_entries=512)


def _jst_day(value: datetime) -> date:
    """Calendar day in Japan; naive timestamps are already Japan time (as in the K-line chart)."""
    return (value.replace(tzinfo=JST) if value.tzinfo is None else value.astimezone(JST)).date()


def daily_best_from_history(points: list[tuple[int, datetime, int]], ceiling: int) -> list[tuple[date, int]]:
    """Best accepted price per Japan day from (store_id, recorded_at, price) history points.

    For each day every store counts once, with its last quote of that day.
    Prices below the floor or above the ceiling are dropped, then the same
    consensus band as the price pages removes outlier stores (when at least
    three stores quote), and the highest remaining quote is that day's best.
    """
    last_by_day_store: dict[date, dict[int, tuple[datetime, int]]] = {}
    for store_id, recorded_at, price in points:
        if not price or price < VALID_PRICE_FLOOR or price > ceiling:
            continue
        day = _jst_day(recorded_at)
        stores = last_by_day_store.setdefault(day, {})
        previous = stores.get(store_id)
        if previous is None or recorded_at > previous[0] or (recorded_at == previous[0] and price > previous[1]):
            stores[store_id] = (recorded_at, int(price))
    result = []
    for day in sorted(last_by_day_store):
        prices = [price for _, price in last_by_day_store[day].values()]
        if len(prices) >= DEFAULT_MIN_STORE_COUNT:
            prices, _, _ = partition_consensus(prices, lambda value: value)
        if prices:
            result.append((day, max(prices)))
    return result


def _history_points(db: Session, product_ids: list[int], since: datetime, until: datetime | None = None) -> list:
    query = db.query(PriceHistory.product_id, PriceHistory.store_id, PriceHistory.recorded_at, PriceHistory.price).join(
        Store, Store.id == PriceHistory.store_id,
    ).filter(
        PriceHistory.product_id.in_(product_ids),
        PriceHistory.recorded_at >= since,
        Store.name.notin_(PUBLIC_PRICE_RESTRICTED_STORES),
    )
    if until is not None:
        query = query.filter(PriceHistory.recorded_at < until)
    return query.all()


def load_daily_best(db: Session, keys: set[tuple[str, str]], today: date | None = None) -> dict[tuple[str, str], list[tuple[date, int]]]:
    """(model, capacity) -> [(day, best accepted price)] for the last TREND_DAYS days, from price_history.

    Days before today come from PAST_DAYS_CACHE when possible; today is always
    read fresh, so the newest value matches the price pages.
    """
    keys = set(sorted(keys)[:MAX_TREND_KEYS])
    if not keys:
        return {}
    today = today or datetime.now(JST).date()
    models = sorted({model for model, _ in keys})
    products = db.query(Product).filter(Product.model.in_(models)).all()
    ids_by_key: dict[tuple[str, str], list[int]] = {}
    ceilings: dict[tuple[str, str], int] = {}
    for product in products:
        key = (product.model, normalise_capacity(product.capacity))
        if key in keys:
            ids_by_key.setdefault(key, []).append(product.id)
            ceilings[key] = max(ceilings.get(key, 0), _price_ceiling(product))
    if not ids_by_key:
        return {}
    # naive bounds in Japan time; history timestamps are compared by the database as stored
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=JST)
    since = today_start - timedelta(days=TREND_DAYS)

    def past_series(key: tuple[str, str]) -> list[tuple[date, int]]:
        rows = _history_points(db, ids_by_key[key], since, today_start)
        return [point for point in daily_best_from_history([(r.store_id, r.recorded_at, r.price) for r in rows], ceilings[key])
                if point[0] < today]

    today_rows = _history_points(db, [pid for ids in ids_by_key.values() for pid in ids], today_start)
    key_by_product = {pid: key for key, ids in ids_by_key.items() for pid in ids}
    today_points: dict[tuple[str, str], list] = {}
    for row in today_rows:
        today_points.setdefault(key_by_product[row.product_id], []).append((row.store_id, row.recorded_at, row.price))

    result = {}
    for key in ids_by_key:
        cache_key = (key, tuple(sorted(ids_by_key[key])), today.isoformat())
        series = list(PAST_DAYS_CACHE.get_or_set(cache_key, lambda key=key: past_series(key)))
        series += [point for point in daily_best_from_history(today_points.get(key, []), ceilings[key]) if point[0] == today]
        if series:
            result[key] = series
    return result


def load_market_snapshots(db: Session, models: set[str]) -> list[dict]:
    """Latest snapshot of every overseas source (younger than 48 hours) for the given models."""
    if not models:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MARKET_MAX_AGE_HOURS)
    latest = db.query(MarketPrice.market, MarketPrice.source, func.max(MarketPrice.collected_at)).filter(
        MarketPrice.collected_at >= cutoff,
    ).group_by(MarketPrice.market, MarketPrice.source).all()
    rows: list[dict] = []
    for market, source, collected_at in latest:
        for row in db.query(MarketPrice).filter(
            MarketPrice.market == market,
            MarketPrice.source == source,
            MarketPrice.collected_at == collected_at,
            MarketPrice.model.in_(sorted(models)),
        ):
            rows.append({"market": row.market, "source": row.source, "model": row.model,
                         "capacity": normalise_capacity(row.capacity), "color_code": row.color_code,
                         "price": row.price, "currency": row.currency, "offers": row.offers})
    return rows
