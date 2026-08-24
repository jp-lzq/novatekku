"""Median-based filtering for chart data."""

from __future__ import annotations

from math import isfinite
from statistics import median
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


def _finite_number(value: int | float, *, name: str) -> float:
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def consensus_bounds(
    values: Iterable[int | float],
    *,
    band_percent: float,
    band_floor: int,
) -> tuple[float, float, float]:
    prices = [_finite_number(value, name="value") for value in values]
    if not prices:
        raise ValueError("At least one value is required")
    percent = _finite_number(band_percent, name="band_percent")
    floor = _finite_number(band_floor, name="band_floor")
    if percent < 0 or floor < 0:
        raise ValueError("Consensus limits must be non-negative")

    center = float(median(prices))
    band = max(abs(center) * percent, floor)
    return center, center - band, center + band


def partition_consensus(
    items: Iterable[T],
    price_getter: Callable[[T], int | float],
    *,
    band_percent: float,
    band_floor: int,
) -> tuple[list[T], list[T], dict[str, float]]:
    priced_rows = [
        (item, _finite_number(price_getter(item), name="price"))
        for item in items
    ]
    center, lower_bound, upper_bound = consensus_bounds(
        (price for _, price in priced_rows),
        band_percent=band_percent,
        band_floor=band_floor,
    )
    accepted = [item for item, price in priced_rows if lower_bound <= price <= upper_bound]
    rejected = [item for item, price in priced_rows if not lower_bound <= price <= upper_bound]
    return accepted, rejected, {
        "median": center,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }
