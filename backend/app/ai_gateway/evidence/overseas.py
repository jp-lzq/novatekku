"""Compare the Japanese best price with Hong Kong and United States buyback prices."""

from __future__ import annotations

MARKET_CURRENCY = {"hk": "HKD", "us": "USD"}


def to_yen(amount: int | None, currency: str, rates: dict) -> int | None:
    """rates: {"USD": {"rate": 155.7}, ...} = yen per unit (the format of app.pricing.fx_rates)."""
    if amount is None:
        return None
    if currency == "JPY":
        return int(amount)
    rate = (rates.get(currency) or {}).get("rate")
    if not rate:
        return None
    return int(round(amount * float(rate)))


def best_overseas(rows: list[dict], model: str, capacity: str) -> dict[str, dict]:
    """rows: market price snapshots {market, model, capacity, color_code, price, currency, offers}."""
    best: dict[str, dict] = {}
    buyers: dict[str, int] = {}
    for row in rows:
        if row.get("model") != model or str(row.get("capacity")) != capacity:
            continue
        market = row.get("market")
        buyers[market] = buyers.get(market, 0) + max(int(row.get("offers") or 1), 1)
        current = best.get(market)
        if current is None or int(row["price"]) > current["price"]:
            best[market] = {"price": int(row["price"]), "currency": row.get("currency") or MARKET_CURRENCY.get(market, ""),
                            "color": row.get("color_code")}
    for market, quote in best.items():
        quote["buyers"] = buyers[market]  # everyone quoting this phone in that market, not only the best colour
    return best


def compare_markets(japan_best: int | None, overseas: dict[str, dict], rates: dict) -> list[dict]:
    result = []
    for market in ("hk", "us"):
        quote = overseas.get(market)
        if not quote:
            continue
        yen = to_yen(quote["price"], quote["currency"], rates)
        entry = {"market": market, "price": quote["price"], "currency": quote["currency"], "price_jpy": yen,
                 "color": quote["color"], "buyers": quote["buyers"]}
        if yen is not None and japan_best:
            entry["vs_japan"] = yen - japan_best
            entry["vs_japan_percent"] = round((yen - japan_best) / japan_best * 100, 1)
        result.append(entry)
    return sorted(result, key=lambda item: -(item.get("price_jpy") or 0))


# a market whose shops are not named publicly is one store with the market's name
UNNAMED_MARKET_STORES = {"香港"}
STORE_RANKING_SIZE = 5


def store_ranking(rows: list[dict], market: str, model: str, capacity: str, rates: dict,
                  limit: int = STORE_RANKING_SIZE) -> list[dict]:
    """Best named stores of one market for a phone (colours merged per store), best first."""
    best: dict[str, dict] = {}
    for row in rows:
        if row.get("market") != market or row.get("model") != model or str(row.get("capacity")) != capacity:
            continue
        if row.get("store") in UNNAMED_MARKET_STORES:
            continue
        price = int(row["price"])
        if row["store"] not in best or price > best[row["store"]]["price"]:
            best[row["store"]] = {"store": row["store"], "price": price, "currency": row.get("currency") or MARKET_CURRENCY.get(market, "")}
    ranked = sorted(best.values(), key=lambda item: (-item["price"], item["store"]))[:limit]
    for item in ranked:
        item["price_jpy"] = to_yen(item["price"], item["currency"], rates)
    return ranked


def attach_store_rankings(markets: list[dict], store_rows: list[dict], model: str, capacity: str, rates: dict) -> list[dict]:
    """Add the named stores behind each market's price ("which US buyer pays the most")."""
    for entry in markets:
        stores = store_ranking(store_rows, entry["market"], model, capacity, rates)
        if stores:
            entry["stores"] = stores
            entry["best_store"] = stores[0]["store"]
    return markets
