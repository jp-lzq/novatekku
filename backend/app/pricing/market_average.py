from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, median, pstdev
from typing import Iterable

from sqlalchemy.orm import Session

from app.db.models import Price, Product
from app.pricing.current_prices import latest_prices_query
from app.pricing.price_validity import CURRENT_PRICE_MAX_AGE_HOURS

VALID_PRICE_FLOOR = 10000
DEFAULT_FRESHNESS_HOURS = CURRENT_PRICE_MAX_AGE_HOURS
DEFAULT_CONSENSUS_BAND_PERCENT = 0.06
DEFAULT_CONSENSUS_BAND_FLOOR = 5000
DEFAULT_MIN_STORE_COUNT = 3


def _now_like(value: datetime | None) -> datetime:
    if value and value.tzinfo:
        return datetime.now(value.tzinfo)
    return datetime.now()


def _hours_between(newer: datetime, older: datetime | None) -> float | None:
    if not newer or not older:
        return None
    return max((newer - older).total_seconds() / 3600, 0)


def _round_price(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value / 100) * 100)


def _price_ceiling(product: Product | None) -> int:
    if product and product.retail_price and product.retail_price > 0:
        return int(max(product.retail_price * 3, product.retail_price + 300000))
    return 1000000


def _price_row(price: Price, status: str, reason: str | None, lag_hours: float | None) -> dict:
    return {
        "store_id": price.store_id,
        "store_name": price.store.name if price.store else None,
        "price": price.price,
        "scraped_at": price.scraped_at.isoformat() if price.scraped_at else None,
        "lag_hours": round(lag_hours, 2) if lag_hours is not None else None,
        "status": status,
        "reason": reason,
    }


def _weighted_average(prices: list[Price], product_latest: datetime, freshness_hours: int) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for price in prices:
        lag_hours = _hours_between(product_latest, price.scraped_at) or 0.0
        freshness_ratio = min(lag_hours / max(freshness_hours, 1), 1)
        weight = max(0.35, 1 - freshness_ratio * 0.65)
        weighted_sum += price.price * weight
        total_weight += weight
    return weighted_sum / total_weight if total_weight else 0.0


def _confidence_label(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def build_market_average_from_latest_prices(
    product: Product,
    latest_prices: Iterable[Price],
    *,
    freshness_hours: int = DEFAULT_FRESHNESS_HOURS,
    consensus_band_percent: float = DEFAULT_CONSENSUS_BAND_PERCENT,
    consensus_band_floor: int = DEFAULT_CONSENSUS_BAND_FLOOR,
    min_store_count: int = DEFAULT_MIN_STORE_COUNT,
) -> dict:
    rows = list(latest_prices)
    product_latest = max((row.scraped_at for row in rows if row.scraped_at), default=None)
    now = _now_like(product_latest)
    effective_freshness_hours = min(freshness_hours, CURRENT_PRICE_MAX_AGE_HOURS)
    ceiling = _price_ceiling(product)
    accepted_seed: list[Price] = []
    rejected: list[dict] = []

    for row in rows:
        lag_hours = _hours_between(product_latest, row.scraped_at) if product_latest else None
        age_hours = _hours_between(now, row.scraped_at)

        if row.price < VALID_PRICE_FLOOR or row.price > ceiling:
            rejected.append(_price_row(row, "rejected", "invalid_price", lag_hours))
            continue
        if age_hours is not None and age_hours > CURRENT_PRICE_MAX_AGE_HOURS:
            rejected.append(_price_row(row, "rejected", "expired_24h", lag_hours))
            continue
        if lag_hours is not None and lag_hours > effective_freshness_hours:
            rejected.append(_price_row(row, "rejected", "stale_against_latest_round", lag_hours))
            continue
        accepted_seed.append(row)

    fresh_prices = [row.price for row in accepted_seed]
    if not fresh_prices:
        return {
            "product_id": product.id,
            "product_name": product.name,
            "model": product.model,
            "capacity": product.capacity,
            "market_average": None,
            "median_price": None,
            "raw_average": None,
            "best_price": None,
            "low_price": None,
            "spread": None,
            "spread_percent": None,
            "confidence_score": 0,
            "confidence_label": "low",
            "accepted_store_count": 0,
            "fresh_store_count": 0,
            "latest_store_count": len(rows),
            "rejected_store_count": len(rejected),
            "fallback_used": False,
            "latest_scraped_at": product_latest.isoformat() if product_latest else None,
            "filters": {
                "freshness_hours": effective_freshness_hours,
                "current_price_max_age_hours": CURRENT_PRICE_MAX_AGE_HOURS,
                "consensus_band_percent": consensus_band_percent,
                "consensus_band_floor": consensus_band_floor,
                "price_floor": VALID_PRICE_FLOOR,
                "price_ceiling": ceiling,
            },
            "accepted_prices": [],
            "rejected_prices": rejected,
        }

    median_price = float(median(fresh_prices))
    consensus_band = max(median_price * consensus_band_percent, consensus_band_floor)
    lower_bound = median_price - consensus_band
    upper_bound = median_price + consensus_band
    accepted = []

    for row in accepted_seed:
        lag_hours = _hours_between(product_latest, row.scraped_at) if product_latest else None
        if lower_bound <= row.price <= upper_bound:
            accepted.append(row)
        else:
            rejected.append(_price_row(row, "rejected", "consensus_outlier", lag_hours))

    fallback_used = False
    if len(accepted) < min_store_count:
        accepted = accepted_seed
        fallback_used = True
        rejected = [item for item in rejected if item.get("reason") != "consensus_outlier"]

    accepted_values = [row.price for row in accepted]
    weighted = _weighted_average(accepted, product_latest, effective_freshness_hours) if product_latest else mean(accepted_values)
    market_average = _round_price(weighted)
    raw_average = _round_price(mean(fresh_prices))
    best_price = max(accepted_values)
    low_price = min(accepted_values)
    spread = best_price - low_price
    spread_percent = round((spread / market_average) * 100, 2) if market_average else None
    dispersion = (pstdev(accepted_values) / market_average) if len(accepted_values) > 1 and market_average else 0

    store_score = min(len(accepted) / 6, 1)
    fresh_ratio = len(accepted_seed) / len(rows) if rows else 0
    dispersion_score = max(0, 1 - min(dispersion / 0.08, 1))
    confidence_score = int(round((store_score * 0.45 + fresh_ratio * 0.25 + dispersion_score * 0.30) * 100))
    if fallback_used:
        confidence_score = max(confidence_score - 15, 0)

    return {
        "product_id": product.id,
        "product_name": product.name,
        "model": product.model,
        "capacity": product.capacity,
        "market_average": market_average,
        "median_price": _round_price(median_price),
        "raw_average": raw_average,
        "best_price": best_price,
        "low_price": low_price,
        "spread": spread,
        "spread_percent": spread_percent,
        "confidence_score": confidence_score,
        "confidence_label": _confidence_label(confidence_score),
        "accepted_store_count": len(accepted),
        "fresh_store_count": len(accepted_seed),
        "latest_store_count": len(rows),
        "rejected_store_count": len(rejected),
        "fallback_used": fallback_used,
        "latest_scraped_at": product_latest.isoformat() if product_latest else None,
        "filters": {
            "freshness_hours": effective_freshness_hours,
            "current_price_max_age_hours": CURRENT_PRICE_MAX_AGE_HOURS,
            "consensus_band_percent": consensus_band_percent,
            "consensus_band_floor": consensus_band_floor,
            "consensus_lower_bound": int(round(lower_bound)),
            "consensus_upper_bound": int(round(upper_bound)),
            "price_floor": VALID_PRICE_FLOOR,
            "price_ceiling": ceiling,
        },
        "accepted_prices": [
            _price_row(row, "accepted", None, _hours_between(product_latest, row.scraped_at) if product_latest else None)
            for row in sorted(accepted, key=lambda item: item.price, reverse=True)
        ],
        "rejected_prices": rejected,
    }


def build_market_average_for_product(
    db: Session,
    product_id: int,
    *,
    freshness_hours: int = DEFAULT_FRESHNESS_HOURS,
    consensus_band_percent: float = DEFAULT_CONSENSUS_BAND_PERCENT,
    min_store_count: int = DEFAULT_MIN_STORE_COUNT,
) -> dict | None:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    rows = latest_prices_query(db).filter(Price.product_id == product_id).all()
    return build_market_average_from_latest_prices(
        product,
        rows,
        freshness_hours=freshness_hours,
        consensus_band_percent=consensus_band_percent,
        min_store_count=min_store_count,
    )


def build_market_average_batch(
    db: Session,
    *,
    product_ids: list[int] | None = None,
    limit: int | None = None,
    freshness_hours: int = DEFAULT_FRESHNESS_HOURS,
    consensus_band_percent: float = DEFAULT_CONSENSUS_BAND_PERCENT,
    min_store_count: int = DEFAULT_MIN_STORE_COUNT,
) -> list[dict]:
    query = latest_prices_query(db)
    if product_ids:
        query = query.filter(Price.product_id.in_(product_ids))
    rows = query.all()

    grouped: dict[int, list[Price]] = {}
    for row in rows:
        grouped.setdefault(row.product_id, []).append(row)

    products = db.query(Product)
    if product_ids:
        products = products.filter(Product.id.in_(product_ids))
    if limit:
        products = products.limit(limit)

    summaries = []
    for product in products.all():
        if product.id not in grouped:
            continue
        summaries.append(
            build_market_average_from_latest_prices(
                product,
                grouped[product.id],
                freshness_hours=freshness_hours,
                consensus_band_percent=consensus_band_percent,
                min_store_count=min_store_count,
            )
        )
    summaries.sort(key=lambda item: (item.get("confidence_score") or 0, item.get("accepted_store_count") or 0), reverse=True)
    return summaries
