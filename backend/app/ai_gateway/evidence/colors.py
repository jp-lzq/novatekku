"""Colour prices for one model and capacity: "17 Pro 256 シルバー はいくら？".

Stores quote colours in two ways (see app.web.routers.prices._assessment_data):

- ``exact``: a price for each colour.  These fill the colour ranking.
- shared: one price for every colour.  Such a store buys any colour at that
  price, so for a seller of a given colour the best price is the higher of the
  best exact quote for that colour and the best shared quote.

``summarise_colors`` returns the colour ranking, the shared quote, the colour
that pays the most, and, when a colour was asked for, what that colour gets,
where, and how far it is behind the top colour.  Every amount is a quote or a
difference of two quotes, so the answer check can confirm it.
"""

from __future__ import annotations

from .matching import normalise_capacity

LANGUAGES = ("ja", "zh", "en")


def _names(row: dict) -> dict[str, str]:
    code = row.get("color_code") or ""
    return {language: row.get(f"color_name_{language}") or code for language in LANGUAGES}


def _best_by_store(rows: list[dict]) -> dict[str, int]:
    best: dict[str, int] = {}
    for row in rows:
        store, price = row.get("store"), int(row.get("price") or 0)
        if store and price > 0 and price > best.get(store, 0):
            best[store] = price
    return best


def _quote(prices_by_store: dict[str, int]) -> dict | None:
    if not prices_by_store:
        return None
    store, price = min(prices_by_store.items(), key=lambda item: (-item[1], item[0]))
    return {"best_price": price, "best_store": store, "store_count": len(prices_by_store)}


def rows_for(color_rows: list[dict], model: str, capacity: str) -> list[dict]:
    return [row for row in color_rows
            if row.get("model") == model and normalise_capacity(row.get("capacity")) == capacity]


def summarise_colors(color_rows: list[dict], model: str, capacity: str, requested: str | None = None) -> dict | None:
    """None when no store quotes this phone by colour (nothing to say about colours)."""
    rows = rows_for(color_rows, model, capacity)
    if not rows:
        return None
    exact_rows: dict[str, list[dict]] = {}
    names: dict[str, dict[str, str]] = {}
    shared_rows = []
    for row in rows:
        code = row.get("color_code")
        if not code:
            continue
        names.setdefault(code, _names(row))
        if row.get("exact"):
            exact_rows.setdefault(code, []).append(row)
        else:
            shared_rows.append(row)

    colors = []
    for code, code_rows in exact_rows.items():
        quote = _quote(_best_by_store(code_rows))
        if quote:
            colors.append({"code": code, "names": names[code], **quote})
    colors.sort(key=lambda item: (-item["best_price"], item["code"]))
    for rank, color in enumerate(colors, start=1):
        color["rank"] = rank
        color["behind_top"] = colors[0]["best_price"] - color["best_price"]
    shared = _quote(_best_by_store(shared_rows))

    result = {
        "colors": colors,
        "all_colors": shared,
        "top_color": colors[0]["code"] if colors else None,
        "color_spread": colors[0]["best_price"] - colors[-1]["best_price"] if len(colors) > 1 else 0,
        "requested": None,
    }
    if requested:
        result["requested"] = requested_quote(result, requested, names.get(requested))
    return result


def requested_quote(summary: dict, code: str, names: dict[str, str] | None) -> dict:
    """What a seller of colour ``code`` gets: the better of its own best quote and the shared one."""
    own = next((color for color in summary["colors"] if color["code"] == code), None)
    shared = summary.get("all_colors")
    candidates = []
    if own:
        candidates.append(("color", own["best_price"], own["best_store"]))
    if shared:
        candidates.append(("all_colors", shared["best_price"], shared["best_store"]))
    entry = {"code": code, "names": names or {language: code for language in LANGUAGES}, "quoted": bool(candidates)}
    if not candidates:
        return entry
    source, price, store = max(candidates, key=lambda item: (item[1], item[0] == "color"))
    top = summary["colors"][0] if summary["colors"] else None
    entry.update({
        "best_price": price,
        "best_store": store,
        "source": source,  # "color": a price for this colour / "all_colors": a store paying the same for every colour
        "rank": own["rank"] if own else None,
        "color_count": len(summary["colors"]),
        "top_color": top["code"] if top else None,
        "top_color_names": top["names"] if top else None,
        "behind_top": max(top["best_price"] - price, 0) if top and top["code"] != code else 0,
    })
    return entry
