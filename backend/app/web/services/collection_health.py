"""How well each collection source has been working lately.

The admin page used to show only the latest run.  That hides two common
problems: a source that fails again and again, and a source that reports
"success" while most of its pages came back empty (the site changed and only a
few prices are still read).  ``assess`` looks at the recent runs of one source
and returns a state with plain reasons:

- ``failing``   the last FAILING_STREAK runs (or more) all failed
- ``stale``     no successful run within STALE_HOURS although runs keep happening
- ``degraded``  it works, but under half of the runs in the window succeeded,
                or most pages of the recent successful runs were empty
- ``healthy``   none of the above
- ``unsupported`` / ``disabled`` / ``unknown`` (no runs yet) are reported as such
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

FAILING_STREAK = 3
STALE_HOURS = 24
WINDOW_HOURS = 24
LOW_SUCCESS_RATE = 0.5
EMPTY_PAGE_RATIO = 0.5
SUCCESS_STATES = ("success", "partial")

# worst first, for sorting and for the summary
STATES = ("failing", "stale", "degraded", "unknown", "healthy", "unsupported", "disabled")


@dataclass
class RunSnapshot:
    status: str
    started_at: datetime
    detail: dict = field(default_factory=dict)

    @classmethod
    def from_row(cls, status: str, started_at: datetime, detail: str | dict | None) -> "RunSnapshot":
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except ValueError:
                detail = {}
        return cls(status, started_at, detail if isinstance(detail, dict) else {})


@dataclass
class Health:
    state: str
    reasons: list[str] = field(default_factory=list)
    consecutive_failures: int = 0
    runs_in_window: int = 0
    success_rate: float | None = None  # within the window
    empty_page_ratio: float | None = None  # recent successful runs
    last_success_at: datetime | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["last_success_at"] = self.last_success_at.isoformat() if self.last_success_at else None
        return data


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def assess(runs: Iterable[RunSnapshot], *, enabled: bool = True, unsupported: bool = False,
           now: datetime | None = None) -> Health:
    """``runs`` in any order; only their status, start time and page counts are used."""
    if not enabled:
        return Health("disabled", ["収集を停止中"])
    if unsupported:
        return Health("unsupported", ["この収集元は未対応"])
    ordered = sorted(runs, key=lambda run: _aware(run.started_at), reverse=True)
    real = [run for run in ordered if run.status != "unsupported"]
    if not real:
        return Health("unknown", ["まだ収集していない"])
    now = _aware(now or datetime.now(timezone.utc))

    streak = 0
    for run in real:
        if run.status != "failed":
            break
        streak += 1
    successes = [run for run in real if run.status in SUCCESS_STATES]
    last_success = _aware(successes[0].started_at) if successes else None
    window = [run for run in real if _aware(run.started_at) >= now - timedelta(hours=WINDOW_HOURS)]
    rate = (sum(run.status in SUCCESS_STATES for run in window) / len(window)) if window else None

    pages = empty = 0
    for run in successes[:5]:
        pages += int(run.detail.get("pages_total") or 0)
        empty += int(run.detail.get("empty_pages") or 0)
    empty_ratio = (empty / pages) if pages else None

    health = Health("healthy", consecutive_failures=streak, runs_in_window=len(window), success_rate=rate,
                    empty_page_ratio=empty_ratio, last_success_at=last_success)
    if streak >= FAILING_STREAK:
        health.state = "failing"
        health.reasons.append(f"{streak}回連続で失敗")
    elif window and (last_success is None or last_success < now - timedelta(hours=STALE_HOURS)):
        health.state = "stale"
        health.reasons.append(f"{STALE_HOURS}時間以上成功していない")
    if health.state == "healthy":
        if rate is not None and len(window) >= 3 and rate < LOW_SUCCESS_RATE:
            health.state = "degraded"
            health.reasons.append(f"直近{WINDOW_HOURS}時間の成功率 {rate:.0%}")
        if empty_ratio is not None and empty_ratio >= EMPTY_PAGE_RATIO:
            health.state = "degraded"
            health.reasons.append(f"成功しても {empty_ratio:.0%} のページが空（サイトの構成変更の可能性）")
    return health


def summarise(states: Iterable[str]) -> dict[str, int]:
    counts = {state: 0 for state in STATES}
    for state in states:
        counts[state] = counts.get(state, 0) + 1
    return counts
