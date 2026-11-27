"""GET /api/v1/prices/where-to-sell: Japan, Hong Kong and the US side by side for one phone.

For a model + capacity this ranks the three markets by their best buyback
price in yen and says where selling pays the most.  It reuses the AI price
evidence functions, so the card on the site and an AI answer never disagree:

- Japan: the current accepted store prices (same 24-hour window, outlier
  filter and publication rule as the price table), new devices only;
- Hong Kong / US: each source's latest snapshot and each named store's latest
  price from the last 48 hours, converted with the cached exchange rates;
- the recommendation code (``japan_best`` / ``overseas_small`` /
  ``overseas_clear`` / ``japan_only``) and the Japanese price direction.

Collection sources are never named in the answer, only buyers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai_gateway.evidence.global_compare import SMALL_GAP_PERCENT, global_comparison
from app.ai_gateway.evidence.loaders import (
    MARKET_MAX_AGE_HOURS,
    load_daily_best,
    load_market_snapshots,
    load_market_store_snapshots,
)
from app.ai_gateway.evidence.matching import CAPACITY_ORDER, capacity_rank, normalise_capacity
from app.ai_gateway.evidence.overseas import attach_store_rankings, best_overseas, compare_markets
from app.ai_gateway.evidence.quotes import summarise_quotes
from app.ai_gateway.evidence.trend import summarise_trend
from app.db.models import MarketPrice, MarketStore, MarketStorePrice, Price, Product, Store
from app.db.session import get_db
from app.infrastructure.ttl_cache import PUBLIC_PRICE_CACHE
from app.pricing.current_prices import latest_prices_query
from app.pricing.fx_rates import get_cached_fx_rates
from app.web.routers.prices import _accepted_price_keys

router = APIRouter()

NEW_CONDITION = "新品"  # overseas prices are for new devices, so Japan is compared like for like
OVERSEAS_MARKETS = ("hk", "us")
TOP_STORES = 3  # buyers listed under each market


def _fx() -> tuple[dict, str | None]:
    """Rates already in memory or on disk; a request never waits for the rate feed."""
    try:
        cached = get_cached_fx_rates()
    except Exception:
        return {}, None
    return cached.get("rates") or {}, cached.get("last_updated")


def _japan_rows(db: Session, model: str) -> tuple[dict[str, list[dict]], dict[str, datetime]]:
    """capacity -> accepted current store prices of new devices, and capacity -> newest quote time."""
    prices = latest_prices_query(db).filter(
        Product.model == model,
        Product.condition == NEW_CONDITION,
        Store.is_active == 1,
    ).all()
    accepted = _accepted_price_keys(db, sorted({price.product_id for price in prices}))
    rows: dict[str, list[dict]] = {}
    updated: dict[str, datetime] = {}
    for price in prices:
        if (price.product_id, price.store_id, price.price) not in accepted:
            continue
        capacity = normalise_capacity(price.product.capacity)
        if not capacity:
            continue
        rows.setdefault(capacity, []).append({"store": price.store.name, "price": price.price,
                                             "retail_price": price.product.retail_price})
        if price.scraped_at and (capacity not in updated or price.scraped_at > updated[capacity]):
            updated[capacity] = price.scraped_at
    return rows, updated


def _overseas_updated(db: Session, model: str) -> dict[str, str | None]:
    """Newest overseas price time per market for this model (snapshots or named stores)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MARKET_MAX_AGE_HOURS)
    newest: dict[str, datetime] = {}
    snapshots = db.query(MarketPrice.market, func.max(MarketPrice.collected_at)).filter(
        MarketPrice.model == model, MarketPrice.collected_at >= cutoff,
    ).group_by(MarketPrice.market).all()
    stores = db.query(MarketStore.market, func.max(MarketStorePrice.collected_at)).join(
        MarketStore, MarketStore.id == MarketStorePrice.market_store_id,
    ).join(Product, Product.id == MarketStorePrice.product_id).filter(
        Product.model == model, MarketStore.is_active.is_(True), MarketStorePrice.collected_at >= cutoff,
    ).group_by(MarketStore.market).all()
    for market, collected_at in [*snapshots, *stores]:
        if collected_at and (market not in newest or collected_at > newest[market]):
            newest[market] = collected_at
    return {market: newest[market].isoformat() if market in newest else None for market in OVERSEAS_MARKETS}


def _japan_stores(rows: list[dict]) -> list[dict]:
    ranking = summarise_quotes(rows, top=TOP_STORES).get("ranking") or []
    return [{"store": item["store"], "price": item["price"], "currency": "JPY", "price_jpy": item["price"]} for item in ranking]


def _overseas_stores(entry: dict) -> list[dict]:
    return [{"store": item["store"], "price": item["price"], "currency": item["currency"], "price_jpy": item["price_jpy"]}
            for item in (entry.get("stores") or [])[:TOP_STORES]]


def _ranked_without_japan(overseas: list[dict]) -> list[dict]:
    """No Japanese price: still show what abroad pays, but without a recommendation."""
    priced = sorted((entry for entry in overseas if entry.get("price_jpy") is not None), key=lambda entry: -entry["price_jpy"])
    top = priced[0]["price_jpy"] if priced else 0
    return [{"market": entry["market"], "price": entry["price"], "currency": entry["currency"],
             "price_jpy": entry["price_jpy"], "store": entry.get("best_store"), "buyers": entry.get("buyers"),
             "rank": rank, "behind_top": top - entry["price_jpy"]}
            for rank, entry in enumerate(priced, start=1)]


def _change_7d(trend: dict) -> dict | None:
    change = trend.get("change_7d")
    if not change:
        return None
    return {"change": change["change"], "percent": change["percent"], "from_date": change["from_date"]}


def where_to_sell(db: Session, model: str, capacity: str | None) -> dict | None:
    """The comparison for one phone; None when the model is not in the catalogue."""
    if not db.query(Product.id).filter(Product.model == model).first():
        return None
    rates, fx_updated = _fx()
    japan_rows, japan_updated = _japan_rows(db, model)
    market_rows = load_market_snapshots(db, {model})
    store_rows = load_market_store_snapshots(db, {model})

    quoted = {*japan_rows, *(row["capacity"] for row in market_rows), *(row["capacity"] for row in store_rows)}
    capacities = sorted((value for value in quoted if value), key=capacity_rank)
    chosen = capacity or (capacities[0] if capacities else None)
    result = {
        "model": model,
        "capacity": chosen,
        "capacities": capacities,
        "markets": [],
        "advice": None,
        "best_market": None,
        "best_overseas_market": None,
        "overseas_gap": None,
        "overseas_gap_percent": None,
        "small_gap_percent": SMALL_GAP_PERCENT,
        "japan_direction": None,
        "japan_change_7d": None,
        "fx": {"rates": {code: (rates.get(code) or {}).get("rate") for code in ("HKD", "USD")}, "updated_at": fx_updated},
        "updated_at": {"jp": japan_updated[chosen].isoformat() if chosen in japan_updated else None,
                       **_overseas_updated(db, model)},
    }
    if chosen is None or chosen not in capacities:
        return result

    rows = japan_rows.get(chosen, [])
    quotes = summarise_quotes(rows)
    trend = summarise_trend(load_daily_best(db, {(model, chosen)}).get((model, chosen), [])) if rows else {}
    overseas = attach_store_rankings(
        compare_markets(quotes.get("best_price"), best_overseas(market_rows, model, chosen), rates),
        store_rows, model, chosen, rates)
    comparison = global_comparison(quotes, overseas, trend)
    stores = {"jp": _japan_stores(rows), **{entry["market"]: _overseas_stores(entry) for entry in overseas}}

    if comparison is None:
        ranking = _ranked_without_japan(overseas)
        result.update(best_market=ranking[0]["market"] if ranking else None)
    else:
        ranking = comparison["ranking"]
        result.update(
            advice=comparison["advice"],
            best_market=comparison["best_market"],
            best_overseas_market=comparison["best_overseas_market"],
            overseas_gap=comparison["overseas_gap"],
            overseas_gap_percent=comparison["overseas_gap_percent"],
            japan_direction=comparison["japan_direction"],
            japan_change_7d=_change_7d(trend),
        )
    result["markets"] = [{**entry, "stores": stores.get(entry["market"], [])} for entry in ranking]
    return result


@router.get("/prices/where-to-sell")
def get_where_to_sell(
    model: str = Query(..., min_length=1, max_length=100),
    capacity: str | None = Query(None, max_length=10),
    db: Session = Depends(get_db),
):
    """Where one phone sells best: Japan, Hong Kong and the US ranked in yen, with a recommendation.

    ``capacity`` accepts "256", "256GB", "1TB" or "1024"; without it the
    smallest quoted capacity is used.  An unknown model is 404; a known model
    with no price for the capacity gives an empty ``markets`` list and the
    capacities that do have prices.
    """
    model = model.strip()
    wanted = normalise_capacity(capacity) if capacity else None
    if wanted is not None and wanted not in CAPACITY_ORDER:
        raise HTTPException(status_code=422, detail="unknown capacity")
    result = PUBLIC_PRICE_CACHE.get_or_set(("where-to-sell", model, wanted), lambda: where_to_sell(db, model, wanted))
    if result is None:
        raise HTTPException(status_code=404, detail="unknown model")
    return result
