"""Totals when several phones are sold together."""

from __future__ import annotations


def bulk_total(lines: list[dict], excluded: list[dict] | None = None) -> dict | None:
    """lines: {"model", "capacity", "quantity", "best_price", "best_store"} for devices with a single capacity.

    Every line is priced at its own best store, then a single-store option is
    offered: the store that pays the most for the whole set among stores that
    quote every line.  ``excluded`` lists phones of the question that could
    not be priced (no single capacity, unknown model, no quote); they are
    reported so a total is never silently short.
    """
    excluded = list(excluded or [])
    priced = []
    for line in lines:
        if line.get("best_price"):
            priced.append(line)
        else:
            excluded.append({"model": line["model"], "quantity": int(line.get("quantity") or 1), "reason": "no_prices"})
    asked = sum(int(line.get("quantity") or 1) for line in priced) + sum(item["quantity"] for item in excluded)
    if not priced or asked < 2:
        return None
    rows = []
    total = 0
    for line in priced:
        quantity = int(line.get("quantity") or 1)
        subtotal = int(line["best_price"]) * quantity
        total += subtotal
        rows.append({"model": line["model"], "capacity": line["capacity"], "quantity": quantity,
                     "unit_price": int(line["best_price"]), "store": line["best_store"], "subtotal": subtotal})

    single_store = None
    store_totals: dict[str, int] = {}
    complete: set[str] | None = None
    for line in priced:
        prices = {item["store"]: int(item["price"]) for item in line.get("ranking_all") or line.get("ranking") or []}
        complete = set(prices) if complete is None else complete & set(prices)
        for store, price in prices.items():
            store_totals[store] = store_totals.get(store, 0) + price * int(line.get("quantity") or 1)
    if complete:
        store = max(sorted(complete), key=lambda name: store_totals[name])
        single_store = {"store": store, "total": store_totals[store], "difference": store_totals[store] - total}
    return {"lines": rows, "total": total, "phones": sum(row["quantity"] for row in rows), "single_store": single_store,
            "excluded": excluded}
