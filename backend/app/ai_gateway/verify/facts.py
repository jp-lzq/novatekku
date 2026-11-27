"""Every number an answer may quote, taken from the price evidence.

``known_values`` maps a value (per currency) to the facts it can stand for,
for example 208000 -> ["iPhone 17 Pro 256 best price (森森買取)"].  Differences
(including the gap between two phones' best prices, used in comparisons) are
stored as absolute values because answers write "1.18万円安い" without a sign.
``store_prices`` maps a store to the prices it quotes for the phones in question
(plus, for the stores of a store comparison or a target question, the gap
written next to the store's name).
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
                for store in market.get("stores") or []:
                    _add(values, store.get("currency") or market.get("currency") or "", store.get("price"), f"{label} {store.get('store')}")
                    _add(values, "JPY", store.get("price_jpy"), f"{label} {store.get('store')} in yen")
            colors = entry.get("colors") or {}
            for color in colors.get("colors") or []:
                _add(values, "JPY", color.get("best_price"), f"{name} {color.get('code')} ({color.get('best_store')})")
                _add(values, "JPY", color.get("behind_top"), f"{name} {color.get('code')} behind the top colour")
            _add(values, "JPY", (colors.get("all_colors") or {}).get("best_price"), f"{name} every colour")
            _add(values, "JPY", colors.get("color_spread"), f"{name} colour spread")
            requested = colors.get("requested") or {}
            _add(values, "JPY", requested.get("best_price"), f"{name} {requested.get('code')} best")
            _add(values, "JPY", requested.get("behind_top"), f"{name} {requested.get('code')} behind the top colour")
            comparison = entry.get("global") or {}
            _add(values, "JPY", comparison.get("overseas_gap"), f"{name} best overseas vs Japan")
            _add(values, "JPY", comparison.get("spread"), f"{name} global spread")
            for market in comparison.get("ranking") or []:
                _add(values, "JPY", market.get("behind_top"), f"{name} {market.get('market')} behind the top market")
    # comparisons: "17 Pro は 16e より 85,500円高い" is the difference of two best prices
    bests = [
        (f"{item.get('model')} {entry.get('capacity')}", (entry.get("quotes") or {}).get("best_price"))
        for item in evidence.get("items") or []
        for entry in (item.get("capacities") or [])[:6]
        if (entry.get("quotes") or {}).get("best_price")
    ]
    # every pair, also two capacities of one model ("512GB は 256GB より 28,000円高い")
    for index, (name_a, price_a) in enumerate(bests):
        for name_b, price_b in bests[index + 1:]:
            _add(values, "JPY", price_a - price_b, f"{name_a} vs {name_b}")
    for item in (evidence.get("store_compare") or {}).get("items") or []:
        name = f"{item.get('model')} {item.get('capacity')}"
        stores = item.get("stores") or []
        for store in stores:
            _add(values, "JPY", store.get("price"), f"{name} {store.get('store')}")
            _add(values, "JPY", store.get("behind_best"), f"{name} {store.get('store')} behind the best store")
        # "携帯空間はアキモバより 3,500円高い": every pair of asked stores
        for index, store_a in enumerate(stores):
            for store_b in stores[index + 1:]:
                _add(values, "JPY", store_a["price"] - store_b["price"], f"{name} {store_a['store']} vs {store_b['store']}")
        _add(values, "JPY", item.get("best_price"), f"{name} best price ({item.get('best_store')})")
        _add(values, "JPY", item.get("gap_to_best"), f"{name} best store vs the asked stores")
    target = evidence.get("target_price") or {}
    _add(values, "JPY", target.get("target"), "target price")
    for item in target.get("items") or []:
        name = f"{item.get('model')} {item.get('capacity')}"
        _add(values, "JPY", item.get("best_vs_target"), f"{name} best vs target")
        _add(values, "JPY", item.get("shortfall"), f"{name} short of the target")
        _add(values, "JPY", item.get("change_7d"), f"{name} change_7d")
        for store in item.get("stores") or []:
            _add(values, "JPY", store.get("price"), f"{name} {store.get('store')}")
            _add(values, "JPY", store.get("over_target"), f"{name} {store.get('store')} over the target")
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
            # a store's colour price differs from its best price ("シルバーなら 172,000円")
            colors = entry.get("colors") or {}
            quotes = list(colors.get("colors") or []) + [colors.get("all_colors") or {}, colors.get("requested") or {}]
            for quote in quotes:
                if quote.get("best_store") and quote.get("best_price"):
                    prices[quote["best_store"]].add(int(quote["best_price"]))
    # the asked stores may rank below the top 5 ("アキモバは 8位で 160,000円"); a store's gap to the best
    # store or to the target is also written next to its name ("アキモバは最高値より 3,500円安い")
    for item in (evidence.get("store_compare") or {}).get("items") or []:
        for store in item.get("stores") or []:
            prices[store["store"]].add(int(store["price"]))
            if store.get("behind_best"):
                prices[store["store"]].add(int(store["behind_best"]))
    for item in (evidence.get("target_price") or {}).get("items") or []:
        for store in item.get("stores") or []:
            prices[store["store"]].add(int(store["price"]))
            if store.get("over_target"):
                prices[store["store"]].add(int(store["over_target"]))
    for row in price_rows or []:
        if (row.get("model"), str(row.get("capacity"))) in asked and row.get("store") and row.get("price"):
            prices[row["store"]].add(int(row["price"]))
    return dict(prices)
