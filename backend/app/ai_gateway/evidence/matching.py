"""Find the products in the current price table that a recognised device refers to."""

from __future__ import annotations

from dataclasses import dataclass, field

CAPACITY_ORDER = ("64", "128", "256", "512", "1TB", "2TB")


def capacity_rank(capacity: str | None) -> int:
    return CAPACITY_ORDER.index(capacity) if capacity in CAPACITY_ORDER else len(CAPACITY_ORDER)


def normalise_capacity(value) -> str | None:
    """Price rows store "256" or "1TB"; older rows may say "256GB" or "1024"."""
    if value is None:
        return None
    text = str(value).strip().upper().replace(" ", "")
    if text.endswith("GB"):
        text = text[:-2]
    if text in ("1024", "1T"):
        return "1TB"
    if text in ("2048", "2T"):
        return "2TB"
    return text or None


@dataclass
class Match:
    model: str
    capacities: list[str] = field(default_factory=list)  # capacities to report, smallest first
    requested_capacity: str | None = None
    notes: list[str] = field(default_factory=list)  # machine-readable reasons, see NOTES


NOTES = {
    "unknown_model": "the model is not in NOVA's catalogue",
    "no_prices": "the model is known but no store quotes it right now",
    "capacity_not_quoted": "the asked capacity has no quote; other capacities are listed",
    "capacity_missing": "no capacity was given; every quoted capacity is listed",
}


def index_rows(price_rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """model -> capacity -> price rows."""
    index: dict[str, dict[str, list[dict]]] = {}
    for row in price_rows:
        model = row.get("model")
        capacity = normalise_capacity(row.get("capacity"))
        if not model or not capacity or not row.get("price"):
            continue
        index.setdefault(model, {}).setdefault(capacity, []).append(row)
    return index


def match_device(device: dict, index: dict[str, dict[str, list[dict]]], max_capacities: int = 6) -> Match:
    model = device.get("model") or ""
    requested = normalise_capacity(device.get("capacity"))
    match = Match(model=model, requested_capacity=requested)
    if not device.get("known", True):
        match.notes.append("unknown_model")
        return match
    quoted = sorted(index.get(model, {}), key=capacity_rank)
    if not quoted:
        match.notes.append("no_prices")
        return match
    if requested:
        if requested in quoted:
            match.capacities = [requested]
        else:
            match.notes.append("capacity_not_quoted")
            match.capacities = quoted[:max_capacities]
    else:
        match.notes.append("capacity_missing")
        match.capacities = quoted[:max_capacities]
    return match
