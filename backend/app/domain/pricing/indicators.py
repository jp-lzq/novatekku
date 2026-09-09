"""Chart intervals and indicator calculations."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from math import isfinite
from statistics import fmean, pstdev
from zoneinfo import ZoneInfo

TOKYO = ZoneInfo("Asia/Tokyo")
VALID_INTERVALS = frozenset({"1h", "1d", "1w"})


def _validate_interval(interval: str) -> None:
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")


def _finite_values(values: list[float]) -> list[float]:
    numbers = [float(value) for value in values]
    if any(not isfinite(value) for value in numbers):
        raise ValueError("indicator values must be finite")
    return numbers


def local_time(value: datetime, timezone: ZoneInfo = TOKYO) -> datetime:
    # Old price rows do not carry a UTC offset, so treat them as local records.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def bucket_time(value: datetime, interval: str) -> datetime | date:
    _validate_interval(interval)
    local = local_time(value)
    if interval == "1h":
        return local.replace(minute=0, second=0, microsecond=0)
    if interval == "1w":
        return local.date() - timedelta(days=local.weekday())
    return local.date()


def bucket_key(value: datetime | date, interval: str) -> str:
    _validate_interval(interval)
    if isinstance(value, datetime):
        return value.isoformat(timespec="hours")
    return value.isoformat()


def bucket_label(value: datetime | date, interval: str) -> str:
    _validate_interval(interval)
    if isinstance(value, datetime):
        return value.strftime("%m/%d %H:%M")
    if interval == "1w":
        return f"{value.strftime('%m/%d')}週"
    return value.strftime("%m/%d")


def round_value(value: float | None) -> float | None:
    if value is None:
        return None
    if not isfinite(value):
        raise ValueError("indicator value must be finite")
    return round(value, 2)


def sma(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    numbers = _finite_values(values)
    result: list[float | None] = [None] * len(numbers)
    window_sum = 0.0
    for index, value in enumerate(numbers):
        window_sum += value
        if index >= period:
            window_sum -= numbers[index - period]
        if index + 1 >= period:
            result[index] = window_sum / period
    return result


def ema(values: list[float], period: int) -> list[float]:
    # The first sample is also the seed. This matches the chart's old behavior.
    if period < 1:
        raise ValueError("period must be positive")
    numbers = _finite_values(values)
    if not numbers:
        return []
    alpha = 2 / (period + 1)
    result = [numbers[0]]
    for value in numbers[1:]:
        result.append((value * alpha) + (result[-1] * (1 - alpha)))
    return result


def bollinger(
    values: list[float],
    period: int = 20,
    deviations: float = 2.0,
) -> tuple[list[float | None], list[float | None]]:
    if period < 1:
        raise ValueError("period must be positive")
    if not isfinite(deviations) or deviations < 0:
        raise ValueError("deviations must be finite and non-negative")
    numbers = _finite_values(values)
    upper: list[float | None] = [None] * len(numbers)
    lower: list[float | None] = [None] * len(numbers)
    for index in range(period - 1, len(numbers)):
        window = numbers[index - period + 1 : index + 1]
        average = fmean(window)
        deviation = pstdev(window) * deviations
        upper[index] = average + deviation
        lower[index] = average - deviation
    return upper, lower


def _rsi_value(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    return 100 - (100 / (1 + average_gain / average_loss))


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    # Start with a simple average, then continue with Wilder's smoothing.
    if period < 1:
        raise ValueError("period must be positive")
    numbers = _finite_values(values)
    result: list[float | None] = [None] * len(numbers)
    if len(numbers) <= period:
        return result

    changes = [numbers[index] - numbers[index - 1] for index in range(1, period + 1)]
    average_gain = sum(max(change, 0.0) for change in changes) / period
    average_loss = sum(max(-change, 0.0) for change in changes) / period
    result[period] = _rsi_value(average_gain, average_loss)

    for index in range(period + 1, len(numbers)):
        change = numbers[index] - numbers[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        result[index] = _rsi_value(average_gain, average_loss)
    return result


def macd(values: list[float]) -> tuple[list[float], list[float], list[float]]:
    numbers = _finite_values(values)
    fast = ema(numbers, 12)
    slow = ema(numbers, 26)
    line = [
        fast_value - slow_value
        for fast_value, slow_value in zip(fast, slow, strict=True)
    ]
    signal = ema(line, 9)
    histogram = [
        line_value - signal_value
        for line_value, signal_value in zip(line, signal, strict=True)
    ]
    return line, signal, histogram


def indicator_points(
    buckets: list[datetime | date],
    values: list[float | None],
    interval: str,
) -> list[dict[str, str | float]]:
    _validate_interval(interval)
    if len(buckets) != len(values):
        raise ValueError("buckets and values must have the same length")
    points: list[dict[str, str | float]] = []
    for bucket, value in zip(buckets, values, strict=True):
        rounded = round_value(value)
        if rounded is not None:
            points.append({"time": bucket_key(bucket, interval), "value": rounded})
    return points
