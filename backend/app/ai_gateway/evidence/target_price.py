"""Can a phone reach the price the seller hopes for: "20万円以上で売れる？".

For one model and capacity ``assess_target`` says how many stores pay the
target or more and which ones (the best ``MAX_STORES``), how far the best
price is above or below the target, and the 7-day direction of the best price
so an answer can add "prices are falling" or "rising".  Nothing is forecast:
every amount is a quote, the target the user wrote, or a difference of the
two, so the answer check can confirm it.
"""

from __future__ import annotations

MAX_STORES = 5


def assess_target(ranking: list[dict], target: int, trend: dict | None = None) -> dict:
    """``ranking``: every store's best quote, highest first (summarise_quotes(rows, top=len(rows))["ranking"])."""
    target = int(target)
    reached = [entry for entry in ranking if int(entry["price"]) >= target]
    best = ranking[0] if ranking else None
    trend = trend or {}
    change = (trend.get("change_7d") or {}).get("change")
    return {
        "target": target,
        "store_count": len(ranking),
        "reached": bool(reached),
        "reached_count": len(reached),
        "stores": [{"store": entry["store"], "price": int(entry["price"]), "over_target": int(entry["price"]) - target}
                   for entry in reached[:MAX_STORES]],
        "best_price": int(best["price"]) if best else None,
        "best_store": best["store"] if best else None,
        "best_vs_target": int(best["price"]) - target if best else None,
        "shortfall": max(target - int(best["price"]), 0) if best else None,
        "direction": trend.get("direction") if trend.get("direction") in ("up", "down", "flat") else None,
        "change_7d": change,
    }
