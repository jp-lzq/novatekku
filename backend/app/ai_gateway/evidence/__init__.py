"""Price evidence for NOVA AI: the facts an answer about a phone should rest on.

After ``understanding`` has worked out which iPhones a question is about,
this package looks them up and returns, for each model and capacity:

- the current quotes: best store and price, runner-up, ranking, market
  average, comparison with Apple's retail price (quotes.py);
- the price direction over 7 / 30 days and a weekly slope (trend.py);
- Hong Kong and United States prices converted to yen (overseas.py);
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
from .loaders import load_daily_best, load_market_snapshots
from .matching import index_rows, match_device
from .overseas import best_overseas, compare_markets
from .quotes import summarise_quotes
from .render import render_evidence
from .trend import summarise_trend

logger = logging.getLogger(__name__)

VERSION = "evidence-v1"
MAX_DEVICES = 4


def build_price_evidence(
    understanding: dict,
    price_rows: list[dict],
    *,
    daily_best: dict | None = None,
    market_rows: list[dict] | None = None,
    fx_rates: dict | None = None,
    fx_updated: str | None = None,
    today: date | None = None,
) -> dict:
    """Pure function: everything it needs is passed in (see collect_price_evidence for the database)."""
    index = index_rows(price_rows)
    daily_best = daily_best or {}
    market_rows = market_rows or []
    fx_rates = fx_rates or {}
    all_devices = understanding.get("devices") or []
    devices = all_devices[:MAX_DEVICES]

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
            entry = {
                "capacity": capacity,
                "quotes": quotes,
                "trend": summarise_trend(daily_best.get((match.model, capacity), []), today),
                "overseas": compare_markets(quotes.get("best_price"),
                                            best_overseas(market_rows, match.model, capacity), fx_rates),
            }
            item["capacities"].append(entry)
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
            fx_rates=fx_rates,
            fx_updated=fx_updated,
        )
    except Exception:
        logger.exception("price evidence failed")
        return {}
