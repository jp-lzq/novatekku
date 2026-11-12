"""Check the amounts and store prices written in an AI answer against the evidence.

Rules:
- an amount is supported when the same value (same currency) is a known fact;
  amounts written as approximate ("約20.8万円", "about ¥208,000") may differ by
  up to 1 %, and amounts written in 万 may differ by the 万 rounding they show;
- when a sentence names a store and one amount, that store must quote that
  amount (a right number at the wrong store is still wrong);
- with no evidence (no phone recognised, no prices) nothing can be checked and
  the status is "no_evidence", never "ok".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

from .amounts import Amount, find_amounts
from .facts import known_values, store_prices

APPROX_TOLERANCE = 0.01
SENTENCE_END = re.compile(r"[。．.!！?？\n]")


@dataclass
class Finding:
    kind: str  # unsupported_amount / wrong_store_price
    text: str  # the amount as written
    value: int
    currency: str
    store: str | None = None
    expected: list[int] = field(default_factory=list)  # what the store really quotes


@dataclass
class Report:
    status: str  # ok / warning / no_evidence / no_amounts
    checked: int = 0
    supported: int = 0
    findings: list[Finding] = field(default_factory=list)
    matched: dict[str, list[str]] = field(default_factory=dict)  # amount text -> facts it matched

    def to_dict(self) -> dict:
        return {**asdict(self), "findings": [asdict(item) for item in self.findings]}


def _precision(text: str) -> int:
    """The rounding an amount was written with: 20.8万 -> 1,000; 20万 -> 10,000; 208,000 -> 1."""
    match = re.search(r"(\d+)(?:\.(\d+))?\s*万", text)
    if not match or re.search(r"万\s*\d", text):
        return 1
    decimals = len(match.group(2) or "")
    return 10000 // (10 ** min(decimals, 4))


def _matches(amount: Amount, values: dict[tuple[str, int], list[str]]) -> list[str]:
    exact = values.get((amount.currency, amount.value))
    if exact:
        return exact
    step = _precision(amount.text)
    tolerance = max(step / 2, amount.value * APPROX_TOLERANCE if amount.approximate else 0)
    if tolerance < 1:
        return []
    labels: list[str] = []
    for (currency, value), facts in values.items():
        if currency == amount.currency and abs(value - amount.value) <= tolerance:
            labels.extend(facts)
    return labels


def _sentences(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for match in SENTENCE_END.finditer(text):
        spans.append((start, match.end()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def verify_answer(answer: str, evidence: dict, price_rows: list[dict] | None = None) -> Report:
    amounts = find_amounts(answer)
    if not evidence or not evidence.get("has_prices"):
        return Report(status="no_evidence", checked=len(amounts))
    if not amounts:
        return Report(status="no_amounts")

    values = known_values(evidence)
    stores = store_prices(evidence, price_rows)
    report = Report(status="ok", checked=len(amounts))
    for amount in amounts:
        labels = _matches(amount, values)
        if labels:
            report.supported += 1
            report.matched[amount.text] = labels[:3]
        else:
            report.findings.append(Finding("unsupported_amount", amount.text, amount.value, amount.currency))

    # store + amount in one sentence: the store must quote that amount
    text = unicodedata.normalize("NFKC", answer)
    for start, end in _sentences(text):
        sentence_amounts = [a for a in amounts if start <= a.start < end and a.currency == "JPY"]
        named = [store for store in stores if store and store in text[start:end]]
        if len(named) != 1 or len(sentence_amounts) != 1:
            continue  # several stores or amounts in one sentence: pairing would be a guess
        store, amount = named[0], sentence_amounts[0]
        quoted = stores[store]
        step = _precision(amount.text)
        tolerance = max(step / 2, amount.value * APPROX_TOLERANCE if amount.approximate else 0)
        if not any(abs(price - amount.value) <= tolerance for price in quoted):
            report.findings.append(Finding("wrong_store_price", amount.text, amount.value, amount.currency,
                                           store=store, expected=sorted(quoted, reverse=True)[:3]))
    if report.findings:
        report.status = "warning"
    return report
