"""Checks performed before replacing the retail-price baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping


PriceKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class RetailBaselineSnapshot:
    prices: Mapping[PriceKey, int]
    observed_at: datetime
    currency: str = "JPY"


def validate_retail_baseline(
    snapshot: RetailBaselineSnapshot,
    required_keys: Iterable[PriceKey],
) -> dict[PriceKey, int]:
    """Return a safe copy only when the incoming snapshot is complete."""
    if snapshot.observed_at.tzinfo is None or snapshot.observed_at.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    if not snapshot.currency or snapshot.currency != snapshot.currency.upper():
        raise ValueError("currency must be an uppercase code")

    prices: dict[PriceKey, int] = {}
    for key, amount in snapshot.prices.items():
        if not isinstance(key, tuple) or len(key) != 2 or not all(str(part).strip() for part in key):
            raise ValueError("price keys must contain an item and a variant")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValueError(f"invalid retail price for {key}")
        prices[(str(key[0]).strip(), str(key[1]).strip())] = amount

    missing = sorted(set(required_keys) - set(prices))
    if missing:
        raise ValueError(f"retail baseline is incomplete: {missing}")
    return prices
