from datetime import datetime, timezone

from app.contracts.analysis import AnalysisProvider, AnalysisRequest, AnalysisResult
from app.contracts.collection import CollectedOffer, CollectionProvider
from app.contracts.repositories import PriceObservation, PriceReader, PriceWriter


class FixedQuoteSource:
    source_key = "fixture"

    def collect(self):
        return [
            CollectedOffer(
                source_key=self.source_key,
                item_key="phone-256",
                amount_minor=98_500,
                currency="JPY",
                observed_at=datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc),
            )
        ]


class EchoAnalyzer:
    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        return AnalysisResult(answer=request.message)


class ListQuoteStore:
    def __init__(self):
        self.rows: list[PriceObservation] = []

    def latest(self, item_key: str):
        return [row for row in self.rows if row.item_key == item_key]

    def save(self, observations):
        existing = set(self.rows)
        new_rows = [row for row in observations if row not in existing]
        self.rows.extend(new_rows)
        return len(new_rows)


def test_plugins_fit_the_declared_interfaces() -> None:
    source = FixedQuoteSource()
    analyzer = EchoAnalyzer()

    assert isinstance(source, CollectionProvider)
    assert isinstance(analyzer, AnalysisProvider)
    assert analyzer.analyze(AnalysisRequest("価格を確認", "ja")).answer == "価格を確認"


def test_replayed_quotes_are_not_inserted_twice() -> None:
    repository = ListQuoteStore()
    observation = PriceObservation(
        item_key="phone-256",
        source_key="fixture",
        amount_minor=98_500,
        currency="JPY",
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert isinstance(repository, PriceReader)
    assert isinstance(repository, PriceWriter)
    assert repository.save([observation]) == 1
    assert repository.save([observation]) == 0
    assert repository.latest("phone-256") == [observation]
