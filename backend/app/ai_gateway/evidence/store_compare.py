"""Store against store: "森森買取とアキモバ、17 Pro 256 はどっちが高い？".

The store names come from the price rows, so a newly collected store is
recognised without a word list.  ``mentioned_stores`` finds them in the
question with a loose match: width, case, spaces and hiragana/katakana do not
matter, and a generic suffix may be left out ("森森" for "森森買取").

``compare_stores`` then gives, for one model and capacity, each asked store's
best quote, its place among all stores, the gap to the best store, which asked
store pays more and by how much, and the asked stores with no quote.  Every
amount is a quote or a difference of two quotes, so the answer check can
confirm it.
"""

from __future__ import annotations

import re

from app.ai_gateway.understanding.normalize import normalize_query

from .quotes import summarise_quotes

MAX_STORES = 4
# words that only say "a shop"; a store may be named without them
_GENERIC_SUFFIXES = ("買取専門店", "買取センター", "買取", "本店", "店", "shop", "store")
# cores too common to stand for one store ("iPhone買取" is not named by "iphone")
_GENERIC_CORES = frozenset({"iphone", "スマホ", "スマートフォン", "携帯", "モバイル", "mobile", "apple"})
_SEPARATORS = r"[\s\-_/・.]*"


def _katakana(text: str) -> str:
    """Hiragana -> katakana, so "あきもば" matches "アキモバ"."""
    return "".join(chr(ord(char) + 0x60) if "ぁ" <= char <= "ゖ" else char for char in text)


def _key(name: str) -> str:
    return re.sub(_SEPARATORS, "", _katakana(normalize_query(name)))


def store_keys(name: str) -> list[str]:
    """The spellings that name ``name``: the full name and the name without a generic suffix."""
    full = _key(name)
    keys = [full] if full else []
    for suffix in _GENERIC_SUFFIXES:
        if full.endswith(suffix) and len(full) > len(suffix):
            core = full[: -len(suffix)]
            long_enough = len(core) >= (3 if core.isascii() else 2)
            if long_enough and core not in _GENERIC_CORES and core not in keys:
                keys.append(core)
            break
    return keys


def _pattern(key: str) -> re.Pattern:
    body = _SEPARATORS.join(re.escape(char) for char in key)
    before = r"(?<![a-z0-9])" if key[0].isascii() and key[0].isalnum() else ""
    after = r"(?![a-z0-9])" if key[-1].isascii() and key[-1].isalnum() else ""
    return re.compile(before + body + after)


def mentioned_stores(text: str | None, store_names) -> list[str]:
    """Stores named in ``text`` (any spelling normalize_query accepts), in the order they appear."""
    if not text:
        return []
    haystack = _katakana(normalize_query(text))
    candidates = sorted(((key, name) for name in set(store_names) if name for key in store_keys(str(name))),
                        key=lambda item: (-len(item[0]), item[1]))
    taken: list[tuple[int, int]] = []
    found: dict[str, int] = {}
    for key, name in candidates:
        for match in _pattern(key).finditer(haystack):
            start, end = match.span()
            if any(start < t_end and end > t_start for t_start, t_end in taken):
                continue  # inside a longer store name already found
            taken.append((start, end))
            found.setdefault(name, start)
    return sorted(found, key=found.get)[:MAX_STORES]


def compare_stores(rows: list[dict], stores: list[str]) -> dict:
    """The asked stores side by side for one model + capacity (``rows`` as for summarise_quotes)."""
    ranking = summarise_quotes(rows, top=max(len(rows), 1)).get("ranking") or []
    position = {entry["store"]: (rank, entry["price"]) for rank, entry in enumerate(ranking, start=1)}
    best = ranking[0] if ranking else None
    quoted, unquoted = [], []
    for store in stores:
        if store in position:
            rank, price = position[store]
            quoted.append({"store": store, "price": price, "rank": rank,
                           "behind_best": best["price"] - price if best else 0})
        else:
            unquoted.append(store)
    quoted.sort(key=lambda entry: (-entry["price"], entry["store"]))
    top = quoted[0] if quoted else None
    second = quoted[1] if len(quoted) > 1 else None
    tie = bool(top and second and top["price"] == second["price"])
    best_is_asked = bool(best and top and top["price"] == best["price"])
    return {
        "stores": quoted,
        "unquoted": unquoted,
        "winner": top["store"] if top and second and not tie else None,
        "tie": tie,
        "gap": top["price"] - second["price"] if second else None,
        "best_store": best["store"] if best else None,
        "best_price": best["price"] if best else None,
        "store_count": len(ranking),
        "best_is_asked": best_is_asked,
        # a store nobody asked about pays more: worth saying ("ほかの店なら …")
        "gap_to_best": best["price"] - top["price"] if best and top and not best_is_asked else None,
    }
