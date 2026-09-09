"""Checks performed before replacing the retail-price baseline."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

PriceKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class RetailBaselineSnapshot:
    prices: Mapping[PriceKey, int]
    observed_at: datetime
    currency: str = "JPY"


def _normalize_key(key: PriceKey) -> PriceKey:
    if (
        not isinstance(key, tuple)
        or len(key) != 2
        or not all(isinstance(part, str) and part.strip() for part in key)
    ):
        raise ValueError("price keys must contain an item and a variant")
    return key[0].strip(), key[1].strip()


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
        normalized = _normalize_key(key)
        if normalized in prices:
            raise ValueError(f"duplicate normalized price key: {normalized}")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValueError(f"invalid retail price for {key}")
        prices[normalized] = amount

    missing = sorted({_normalize_key(key) for key in required_keys} - set(prices))
    if missing:
        raise ValueError(f"retail baseline is incomplete: {missing}")
    return prices
