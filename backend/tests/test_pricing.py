from datetime import datetime, timezone
from math import inf, nan, sqrt

import pytest

from app.domain.pricing.retail_baseline import RetailBaselineSnapshot, validate_retail_baseline
from app.domain.pricing.consensus import consensus_bounds, partition_consensus
from app.domain.pricing.indicators import (
    bollinger,
    bucket_time,
    ema,
    indicator_points,
    macd,
    rsi,
    sma,
)


def test_consensus_partitions_values_and_reads_each_item_once() -> None:
    calls = 0

    def read_price(value: int) -> int:
        nonlocal calls
        calls += 1
        return value

    accepted, rejected, details = partition_consensus(
        [100, 101, 500],
        read_price,
        band_percent=0.1,
        band_floor=5,
    )

    assert calls == 3
    assert accepted == [100, 101]
    assert rejected == [500]
    assert details == pytest.approx({"median": 101, "lower_bound": 90.9, "upper_bound": 111.1})


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_consensus_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        consensus_bounds([100, value], band_percent=0.1, band_floor=5)


def test_moving_averages_have_defined_seed_behavior() -> None:
    assert sma([1, 2, 3, 4], 3) == [None, None, 2, 3]
    assert ema([1, 2, 3], 2) == pytest.approx([1, 5 / 3, 23 / 9])


def test_bollinger_uses_population_standard_deviation() -> None:
    upper, lower = bollinger([1, 2, 3], period=3)
    deviation = 2 * sqrt(2 / 3)
    assert upper == pytest.approx([None, None, 2 + deviation])
    assert lower == pytest.approx([None, None, 2 - deviation])


def test_rsi_uses_wilder_smoothing() -> None:
    assert rsi([10, 11, 10, 12, 11, 13], period=3) == pytest.approx(
        [None, None, None, 75, 54.5454545, 75]
    )


def test_macd_has_stable_numeric_output() -> None:
    line, signal, histogram = macd([1, 2, 3])
    assert line == pytest.approx([0, 0.0797720798, 0.2211345687])
    assert signal == pytest.approx([0, 0.0159544160, 0.0569904465])
    assert histogram == pytest.approx([0, 0.0638176638, 0.1641441222])


def test_time_buckets_reject_unknown_intervals() -> None:
    with pytest.raises(ValueError, match="Unsupported interval"):
        bucket_time(datetime.now(timezone.utc), "5m")


def test_indicator_points_require_matching_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        indicator_points([datetime.now(timezone.utc)], [1.0, 2.0], "1h")


def test_retail_baseline_requires_a_complete_snapshot() -> None:
    snapshot = RetailBaselineSnapshot(
        prices={
            ("phone", "small"): 98_000,
            ("phone", "large"): 128_000,
        },
        observed_at=datetime.now(timezone.utc),
    )

    assert validate_retail_baseline(
        snapshot,
        {("phone", "small"), ("phone", "large")},
    ) == dict(snapshot.prices)


def test_retail_baseline_rejects_partial_or_unusable_updates() -> None:
    partial = RetailBaselineSnapshot(
        prices={("phone", "small"): 98_000},
        observed_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="incomplete"):
        validate_retail_baseline(partial, {("phone", "small"), ("phone", "large")})

    invalid = RetailBaselineSnapshot(
        prices={("phone", "small"): 0},
        observed_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="invalid retail price"):
        validate_retail_baseline(invalid, {("phone", "small")})
