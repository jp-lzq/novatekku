"""Common record shape returned by quote sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class CollectedOffer:
    source_key: str
    item_key: str
    amount_minor: int
    currency: str
    observed_at: datetime
    metadata: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class CollectionProvider(Protocol):
    @property
    def source_key(self) -> str: ...

    def collect(self) -> Sequence[CollectedOffer]: ...
