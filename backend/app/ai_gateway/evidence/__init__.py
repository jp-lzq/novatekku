"""Price evidence for NOVA AI: the facts an answer about a phone should rest on.

After ``understanding`` has worked out which iPhones a question is about,
this package looks them up and returns, for each model and capacity:

- the current quotes: best store and price, runner-up, ranking, market
  average, comparison with Apple's retail price (quotes.py);
- the price direction over 7 / 30 days and a weekly slope (trend.py);
- Hong Kong and United States prices converted to yen (overseas.py) and
  every market ranked with a recommendation of where to sell (global_compare.py);
- the price of each colour and of the colour asked about (colors.py);
- the stores named in the question side by side (store_compare.py);
- whether the price the user hopes for is reached, and where (target_price.py);
- a total when several phones are sold together (bulk.py).

Everything is computed from data NOVA already stores, so the AI core can
quote exact numbers instead of guessing them.  The result is attached to
every AIRequest as ``price_evidence``.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from .bulk import bulk_total
from .colors import summarise_colors
from .global_compare import global_comparison
from .loaders import load_color_rows, load_daily_best, load_market_snapshots, load_market_store_snapshots
from .matching import index_rows, match_device
from .overseas import attach_store_rankings, best_overseas, compare_markets
from .quotes import summarise_quotes
from .render import render_evidence
from .store_compare import compare_stores, mentioned_stores
from .target_price import assess_target
from .trend import summarise_trend

logger = logging.getLogger(__name__)

VERSION = "evidence-v1"
MAX_DEVICES = 4
MAX_COMPARED_CAPACITIES = 3  # store or target comparison per model when no capacity was given


def build_price_evidence(
    understanding: dict,
    price_rows: list[dict],
    *,
    daily_best: dict | None = None,
    market_rows: list[dict] | None = None,
    market_store_rows: list[dict] | None = None,
    color_rows: list[dict] | None = None,
    fx_rates: dict | None = None,
    fx_updated: str | None = None,
    today: date | None = None,
) -> dict:
    """Pure function: everything it needs is passed in (see collect_price_evidence for the database)."""
    index = index_rows(price_rows)
    daily_best = daily_best or {}
    market_rows = market_rows or []
    market_store_rows = market_store_rows or []
    color_rows = color_rows or []
    fx_rates = fx_rates or {}
    all_devices = understanding.get("devices") or []
    devices = all_devices[:MAX_DEVICES]
    asked_stores = mentioned_stores(understanding.get("text"), {row.get("store") for row in price_rows})
    target = understanding.get("target_price") if understanding.get("intent") == "target_price" else None
    store_lines = []
    target_lines = []

    items = []
    bulk_lines = []
    bulk_excluded = []
    for device in devices:
        match = match_device(device, index)
        item = {
            "model": match.model,
            "requested_capacity": match.requested_capacity,
            "color": device.get("color"),
            "condition": device.get("condition"),
            "quantity": int(device.get("quantity") or 1),
            "notes": match.notes,
            "capacities": [],
        }
        # only a capacity the user wrote is totalled; a guessed one never is
        priced_capacity = match.requested_capacity if match.capacities == [match.requested_capacity] else None
        if not priced_capacity:
            reason = match.notes[0] if match.notes else "no_prices"
            bulk_excluded.append({"model": match.model, "capacity": match.requested_capacity,
                                  "quantity": item["quantity"], "reason": reason})
        for capacity in match.capacities:
            rows = index[match.model][capacity]
            quotes = summarise_quotes(rows)
            trend = summarise_trend(daily_best.get((match.model, capacity), []), today)
            overseas = attach_store_rankings(
                compare_markets(quotes.get("best_price"), best_overseas(market_rows, match.model, capacity), fx_rates),
                market_store_rows, match.model, capacity, fx_rates)
            entry = {
                "capacity": capacity,
                "quotes": quotes,
                "trend": trend,
                "overseas": overseas,
                "global": global_comparison(quotes, overseas, trend) if overseas else None,
                "colors": summarise_colors(color_rows, match.model, capacity, device.get("color")),
            }
            item["capacities"].append(entry)
            if quotes.get("best_price") and len(item["capacities"]) <= MAX_COMPARED_CAPACITIES:
                if asked_stores:
                    store_lines.append({"model": match.model, "capacity": capacity, **compare_stores(rows, asked_stores)})
                if target:
                    ranking_all = summarise_quotes(rows, top=len(rows)).get("ranking", [])
                    target_lines.append({"model": match.model, "capacity": capacity,
                                         **assess_target(ranking_all, target, trend)})
            if capacity == priced_capacity:
                bulk_lines.append({
                    "model": match.model, "capacity": capacity, "quantity": item["quantity"],
                    "best_price": quotes.get("best_price"), "best_store": quotes.get("best_store"),
                    "ranking_all": summarise_quotes(rows, top=len(rows)).get("ranking", []),
                })
        items.append(item)

    result = {
        "version": VERSION,
        "intent": understanding.get("intent"),
        "items": items,
        "bulk": bulk_total(bulk_lines, bulk_excluded) if _wants_total(understanding, devices) else None,
        "devices_not_shown": [device.get("model") for device in all_devices[MAX_DEVICES:]],
        "fx_updated": fx_updated,
        "follow_up_capacity": understanding.get("follow_up_capacity"),
        "has_prices": any(entry["quotes"].get("best_price") for item in items for entry in item["capacities"]),
        "store_compare": {"stores": asked_stores, "items": store_lines} if asked_stores else None,
        "target_price": {"target": int(target), "items": target_lines} if target else None,
    }
    result["lines"] = {language: render_evidence(result, language) for language in ("ja", "zh", "en")}
    return result


def _wants_total(understanding: dict, devices: list[dict]) -> bool:
    """A total only when it was asked for or several units of a phone are sold ("17 pro x2")."""
    return understanding.get("intent") == "bulk_quote" or any(int(device.get("quantity") or 1) > 1 for device in devices)


def collect_price_evidence(db: Session, understanding: dict, price_rows: list[dict], fx_rates: dict | None = None,
                           fx_updated: str | None = None) -> dict:
    """Read the extra data the evidence needs and build it.  Never raises: a failure gives an empty dict."""
    try:
        index = index_rows(price_rows)
        keys = set()
        for device in (understanding.get("devices") or [])[:MAX_DEVICES]:
            match = match_device(device, index)
            keys.update((match.model, capacity) for capacity in match.capacities)
        return build_price_evidence(
            understanding,
            price_rows,
            daily_best=load_daily_best(db, keys),
            market_rows=load_market_snapshots(db, {model for model, _ in keys}),
            market_store_rows=load_market_store_snapshots(db, {model for model, _ in keys}),
            color_rows=load_color_rows(db, {model for model, _ in keys}),
            fx_rates=fx_rates,
            fx_updated=fx_updated,
        )
    except Exception:
        logger.exception("price evidence failed")
        return {}
