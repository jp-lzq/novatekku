"""Japan, Hong Kong and the United States side by side, with a plain recommendation.

For one phone (model + capacity) this ranks every market by its best buyback
price in yen and works out where to sell:

- ``japan_best``      Japan already pays the most: sell in Japan.
- ``overseas_small``  a market abroad pays a little more, but less than
                      ``SMALL_GAP_PERCENT``: shipping, fees, customs and the
                      exchange rate usually eat that, so Japan is still the
                      practical choice.
- ``overseas_clear``  a market abroad pays clearly more: worth it only for
                      someone who is there or can sell there; the costs above
                      still apply.
- ``japan_only``      no usable overseas price (or no exchange rate).

``japan_direction`` (rising / falling / flat) comes from the Japanese trend so
an answer can add "prices are falling, do not wait".  Nothing here is
invented: every amount is a price already in the evidence or a difference of
two of them, so the answer check can confirm it.
"""

from __future__ import annotations

SMALL_GAP_PERCENT = 5.0  # below this an overseas lead is eaten by shipping, fees and the exchange rate
JAPAN = "jp"


def _japan_entry(quotes: dict) -> dict | None:
    price = quotes.get("best_price")
    if not price:
        return None
    return {"market": JAPAN, "price": int(price), "currency": "JPY", "price_jpy": int(price),
            "store": quotes.get("best_store"), "buyers": quotes.get("store_count")}


def _overseas_entry(market: dict) -> dict | None:
    if market.get("price_jpy") is None:
        return None
    return {"market": market["market"], "price": market["price"], "currency": market["currency"],
            "price_jpy": int(market["price_jpy"]), "store": market.get("best_store"), "buyers": market.get("buyers")}


def _percent(part: int, whole: int) -> float | None:
    return round(part / whole * 100, 1) if whole else None


def advice_for(gap: int | None, gap_percent: float | None) -> str:
    """The recommendation for an overseas lead of ``gap`` yen (``gap_percent`` of the Japanese price)."""
    if gap is None:
        return "japan_only"
    if gap <= 0:
        return "japan_best"
    if gap_percent is not None and gap_percent < SMALL_GAP_PERCENT:
        return "overseas_small"
    return "overseas_clear"


def global_comparison(quotes: dict, overseas: list[dict], trend: dict | None = None) -> dict | None:
    """Every market ranked by yen with the recommendation; None without a Japanese price."""
    japan = _japan_entry(quotes or {})
    if japan is None:
        return None
    abroad = [entry for entry in (_overseas_entry(market) for market in overseas or []) if entry]
    ranking = sorted([japan, *abroad], key=lambda entry: (-entry["price_jpy"], entry["market"] != JAPAN))
    top = ranking[0]["price_jpy"]
    for rank, entry in enumerate(ranking, start=1):
        entry["rank"] = rank
        entry["behind_top"] = top - entry["price_jpy"]

    best_abroad = max(abroad, key=lambda entry: entry["price_jpy"]) if abroad else None
    gap = best_abroad["price_jpy"] - japan["price_jpy"] if best_abroad else None
    gap_percent = _percent(gap, japan["price_jpy"]) if gap is not None else None
    direction = (trend or {}).get("direction")
    return {
        "ranking": ranking,
        "best_market": ranking[0]["market"],
        "japan_price": japan["price_jpy"],
        "japan_store": japan["store"],
        "japan_rank": japan["rank"],
        "best_overseas_market": best_abroad["market"] if best_abroad else None,
        "best_overseas_store": best_abroad["store"] if best_abroad else None,
        "overseas_gap": gap,
        "overseas_gap_percent": gap_percent,
        "spread": top - ranking[-1]["price_jpy"] if len(ranking) > 1 else 0,
        "advice": advice_for(gap, gap_percent),
        "japan_direction": direction if direction in ("up", "down", "flat") else None,
    }
