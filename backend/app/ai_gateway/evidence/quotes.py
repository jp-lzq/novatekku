"""Summarise the current store quotes for one model and capacity."""

from __future__ import annotations

from statistics import median


def summarise_quotes(rows: list[dict], top: int = 5) -> dict:
    """Best price, runner-up, ranking and the market figures for one product.

    ``rows`` are price rows of a single model + capacity (one per store).  The
    same store may appear twice when it lists colours separately; only its best
    quote counts.
    """
    best_by_store: dict[str, dict] = {}
    for row in rows:
        store = str(row.get("store") or "")
        price = int(row.get("price") or 0)
        if not store or price <= 0:
            continue
        if store not in best_by_store or price > int(best_by_store[store]["price"]):
            best_by_store[store] = row
    ranked = sorted(best_by_store.values(), key=lambda row: (-int(row["price"]), str(row["store"])))
    if not ranked:
        return {"store_count": 0}

    prices = [int(row["price"]) for row in ranked]
    best = ranked[0]
    retail = next((int(row["retail_price"]) for row in ranked if row.get("retail_price")), None)
    market_average = next((row.get("market_average") for row in ranked if row.get("market_average")), None)
    summary = {
        "store_count": len(ranked),
        "best_price": prices[0],
        "best_store": best["store"],
        "best_store_url": best.get("store_url"),
        "runner_up_price": prices[1] if len(prices) > 1 else None,
        "lead_over_runner_up": prices[0] - prices[1] if len(prices) > 1 else None,
        "lowest_price": prices[-1],
        "median_price": int(median(prices)),
        "spread": prices[0] - prices[-1],
        "market_average": market_average,
        "market_confidence": next((row.get("market_confidence") for row in ranked if row.get("market_confidence")), None),
        "retail_price": retail,
        "best_vs_retail": prices[0] - retail if retail else None,
        "best_vs_retail_percent": round((prices[0] - retail) / retail * 100, 1) if retail else None,
        "ranking": [{"store": row["store"], "price": int(row["price"])} for row in ranked[:top]],
        "sponsored_stores": sorted(row["store"] for row in ranked if row.get("is_sponsored")),
    }
    return summary
