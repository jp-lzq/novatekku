"""Interfaces for plugging an analysis backend into the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    message: str
    locale: str
    context: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    answer: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@runtime_checkable
class AnalysisProvider(Protocol):
    def analyze(self, request: AnalysisRequest) -> AnalysisResult: ...
