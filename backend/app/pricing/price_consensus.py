from __future__ import annotations

from statistics import median
from typing import Callable, Iterable, TypeVar


DEFAULT_CONSENSUS_BAND_PERCENT = 0.06
DEFAULT_CONSENSUS_BAND_FLOOR = 5000
DEFAULT_MIN_STORE_COUNT = 3

T = TypeVar("T")


def consensus_bounds(
    values: Iterable[int | float],
    *,
    band_percent: float = DEFAULT_CONSENSUS_BAND_PERCENT,
    band_floor: int = DEFAULT_CONSENSUS_BAND_FLOOR,
) -> tuple[float, float, float]:
    prices = [float(value) for value in values]
    if not prices:
        raise ValueError("At least one price is required")

    center = float(median(prices))
    band = max(center * band_percent, float(band_floor))
    return center, center - band, center + band


def partition_consensus(
    items: Iterable[T],
    price_getter: Callable[[T], int | float],
    *,
    band_percent: float = DEFAULT_CONSENSUS_BAND_PERCENT,
    band_floor: int = DEFAULT_CONSENSUS_BAND_FLOOR,
) -> tuple[list[T], list[T], dict[str, float]]:
    rows = list(items)
    center, lower_bound, upper_bound = consensus_bounds(
        (price_getter(item) for item in rows),
        band_percent=band_percent,
        band_floor=band_floor,
    )
    accepted = [item for item in rows if lower_bound <= price_getter(item) <= upper_bound]
    rejected = [item for item in rows if not lower_bound <= price_getter(item) <= upper_bound]
    return accepted, rejected, {
        "median": center,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }
