"""Price direction from the daily best price history (see loaders.daily_best_from_history).

Two simple, explainable measures:

- change over 7 and 30 days: today's best price minus the best price on the
  closest earlier day with data;
- slope: an ordinary least-squares line through the last 30 days of closes,
  reported as yen per week, only when those days span at least two weeks.  (Least squares = the straight line with the
  smallest total squared distance to the points.)

"flat" means the 7-day change is smaller than 1 % either way.
"""

from __future__ import annotations

from datetime import date, timedelta

FLAT_PERCENT = 1.0
MIN_SLOPE_SPAN_DAYS = 14  # a slope over a few days after launch says more about the launch than the trend


def _closest_on_or_before(series: list[tuple[date, int]], day: date) -> tuple[date, int] | None:
    candidates = [point for point in series if point[0] <= day]
    return candidates[-1] if candidates else None


def _change(series: list[tuple[date, int]], latest: tuple[date, int], days: int) -> dict | None:
    earlier = _closest_on_or_before(series, latest[0] - timedelta(days=days))
    if not earlier or earlier[1] <= 0:
        return None
    change = latest[1] - earlier[1]
    return {"from_date": earlier[0].isoformat(), "from_price": earlier[1], "change": change,
            "percent": round(change / earlier[1] * 100, 1)}


def weekly_slope(series: list[tuple[date, int]]) -> float | None:
    if len(series) < 3:
        return None
    origin = series[0][0]
    xs = [(day - origin).days for day, _ in series]
    ys = [price for _, price in series]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance == 0:
        return None
    slope_per_day = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / variance
    return round(slope_per_day * 7)


def summarise_trend(points: list[tuple[date, int]], today: date | None = None) -> dict:
    """``points``: (day, best price that day), any order, duplicates allowed (last one wins)."""
    by_day: dict[date, int] = {}
    for day, price in points:
        if price and price > 0:
            by_day[day] = int(price)
    series = sorted(by_day.items())
    if today is not None:
        series = [point for point in series if point[0] <= today]
    if not series:
        return {"days_of_data": 0, "direction": "unknown"}
    latest = series[-1]
    recent = [point for point in series if point[0] >= latest[0] - timedelta(days=30)]
    change_7d = _change(series, latest, 7)
    direction = "unknown"
    if change_7d:
        if abs(change_7d["change"]) / change_7d["from_price"] * 100 < FLAT_PERCENT:
            direction = "flat"
        else:
            direction = "up" if change_7d["change"] > 0 else "down"
    return {
        "days_of_data": len(series),
        "latest_date": latest[0].isoformat(),
        "latest_price": latest[1],
        "change_7d": change_7d,
        "change_30d": _change(series, latest, 30),
        "slope_per_week": weekly_slope(recent) if (recent[-1][0] - recent[0][0]).days >= MIN_SLOPE_SPAN_DAYS else None,
        "high_30d": max(price for _, price in recent),
        "low_30d": min(price for _, price in recent),
        "direction": direction,
    }
