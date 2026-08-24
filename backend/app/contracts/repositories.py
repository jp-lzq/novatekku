"""Read and write boundaries for normalized quotes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class PriceObservation:
    item_key: str
    source_key: str
    amount_minor: int
    currency: str
    observed_at: datetime


@runtime_checkable
class PriceReader(Protocol):
    def latest(self, item_key: str) -> Sequence[PriceObservation]: ...


@runtime_checkable
class PriceWriter(Protocol):
    # Replaying the same batch must not create duplicate rows.
    def save(self, observations: Sequence[PriceObservation]) -> int: ...
