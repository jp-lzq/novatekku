"""Every number an answer may quote, taken from the price evidence.

``known_values`` maps a value (per currency) to the facts it can stand for,
for example 208000 -> ["iPhone 17 Pro 256 best price (森森買取)"].  Differences
are stored as absolute values because answers write "1.18万円安い" without a sign.
``store_prices`` maps a store to the prices it quotes for the phones in question.
"""

from __future__ import annotations

from collections import defaultdict


def _add(values: dict, currency: str, value, label: str) -> None:
    if value is None:
        return
    try:
        number = abs(int(round(float(value))))
    except (TypeError, ValueError):
        return
    if number > 0:
        values[(currency, number)].append(label)


def known_values(evidence: dict) -> dict[tuple[str, int], list[str]]:
    values: dict[tuple[str, int], list[str]] = defaultdict(list)
    for item in evidence.get("items") or []:
        model = item.get("model", "")
        for entry in item.get("capacities") or []:
            name = f"{model} {entry.get('capacity')}"
            quotes = entry.get("quotes") or {}
            _add(values, "JPY", quotes.get("best_price"), f"{name} best price ({quotes.get('best_store')})")
            for key in ("runner_up_price", "lowest_price", "median_price", "market_average", "retail_price",
                        "best_vs_retail", "lead_over_runner_up", "spread"):
                _add(values, "JPY", quotes.get(key), f"{name} {key}")
            for rank in quotes.get("ranking") or []:
                _add(values, "JPY", rank.get("price"), f"{name} {rank.get('store')}")
            trend = entry.get("trend") or {}
            for key in ("latest_price", "high_30d", "low_30d", "slope_per_week"):
                _add(values, "JPY", trend.get(key), f"{name} {key}")
            for window in ("change_7d", "change_30d"):
                change = trend.get(window) or {}
                _add(values, "JPY", change.get("change"), f"{name} {window}")
                _add(values, "JPY", change.get("from_price"), f"{name} {window} start")
            for market in entry.get("overseas") or []:
                label = f"{name} {market.get('market')}"
                _add(values, market.get("currency") or "", market.get("price"), label)
                _add(values, "JPY", market.get("price_jpy"), f"{label} in yen")
                _add(values, "JPY", market.get("vs_japan"), f"{label} vs Japan")
    bulk = evidence.get("bulk") or {}
    _add(values, "JPY", bulk.get("total"), "bulk total")
    for line in bulk.get("lines") or []:
        _add(values, "JPY", line.get("unit_price"), f"bulk {line.get('model')} unit")
        _add(values, "JPY", line.get("subtotal"), f"bulk {line.get('model')} subtotal")
    single = bulk.get("single_store") or {}
    _add(values, "JPY", single.get("total"), f"bulk single store ({single.get('store')})")
    _add(values, "JPY", single.get("difference"), "bulk single store difference")
    return dict(values)


def store_prices(evidence: dict, price_rows: list[dict] | None = None) -> dict[str, set[int]]:
    """store -> prices it quotes for the phones in the evidence (all capacities asked about)."""
    prices: dict[str, set[int]] = defaultdict(set)
    asked = set()
    for item in evidence.get("items") or []:
        for entry in item.get("capacities") or []:
            asked.add((item.get("model"), str(entry.get("capacity"))))
            for rank in (entry.get("quotes") or {}).get("ranking") or []:
                if rank.get("store") and rank.get("price"):
                    prices[rank["store"]].add(int(rank["price"]))
    for row in price_rows or []:
        if (row.get("model"), str(row.get("capacity"))) in asked and row.get("store") and row.get("price"):
            prices[row["store"]].add(int(row["price"]))
    return dict(prices)
