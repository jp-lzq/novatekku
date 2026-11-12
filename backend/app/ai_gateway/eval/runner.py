"""Score the question understanding against a fixed set of graded questions.

Each case in cases.jsonl is one JSON object:

    {"id": "ja-price-01", "lang": "ja", "q": "17プロマ 256 いくら",
     "history": ["…earlier user messages…"],            # optional, for follow-ups
     "expect": {"intent": "price_quote",
                "models": ["iPhone 17 Pro Max"], "capacities": ["256"],
                "colors": [...], "quantities": [...], "markets": [...]},
     "known_gap": "why this one is still answered wrongly"}   # optional

Only the fields written in "expect" are graded.  A case passes when every
graded field matches.  Cases marked known_gap are counted but reported
separately, so the score never hides a weakness and a fix shows up at once.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.ai_gateway.context import resolve_message

CASES_FILE = Path(__file__).with_name("cases.jsonl")
FIELDS = ("intent", "models", "capacities", "colors", "quantities", "markets")


@dataclass
class CaseResult:
    case_id: str
    lang: str
    passed: bool
    known_gap: bool
    fields: dict[str, bool] = field(default_factory=dict)  # graded field -> correct
    got: dict = field(default_factory=dict)


@dataclass
class Score:
    total: int = 0
    passed: int = 0
    by_field: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))  # field -> [ok, graded]
    by_lang: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    failures: list[CaseResult] = field(default_factory=list)
    known_gaps_fixed: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "accuracy": round(self.accuracy, 4),
            "by_field": {name: {"correct": ok, "graded": graded, "accuracy": round(ok / graded, 4) if graded else None}
                         for name, (ok, graded) in sorted(self.by_field.items())},
            "by_lang": {name: {"passed": ok, "total": total} for name, (ok, total) in sorted(self.by_lang.items())},
            "failures": [{"id": item.case_id, "fields": item.fields, "got": item.got, "known_gap": item.known_gap}
                         for item in self.failures],
            "known_gaps_fixed": self.known_gaps_fixed,
        }


def load_cases(path: Path = CASES_FILE) -> list[dict]:
    cases = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        case = json.loads(line)
        if not case.get("id") or not case.get("q") or not isinstance(case.get("expect"), dict):
            raise ValueError(f"{path.name}:{number}: id, q and expect are required")
        unknown = set(case["expect"]) - set(FIELDS)
        if unknown:
            raise ValueError(f"{path.name}:{number}: unknown expect fields {sorted(unknown)}")
        cases.append(case)
    ids = [case["id"] for case in cases]
    duplicates = {case_id for case_id in ids if ids.count(case_id) > 1}
    if duplicates:
        raise ValueError(f"duplicate case ids: {sorted(duplicates)}")
    return cases


def _history(messages: list[str]) -> list[dict]:
    history = []
    for message in messages:
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": "(answer)"}]
    return history


def observe(case: dict) -> dict:
    """What the understanding produced, in the same shape as "expect"."""
    result = resolve_message(case["q"], _history(case.get("history") or []))
    devices = result["devices"]
    return {
        "intent": result["intent"],
        "models": [device["model"] for device in devices],
        "capacities": [device["capacity"] for device in devices],
        "colors": [device["color"] for device in devices],
        "quantities": [device["quantity"] for device in devices],
        "markets": [market for market in result["markets"] if market != "jp"],
    }


def grade(case: dict) -> CaseResult:
    got = observe(case)
    fields = {name: got[name] == expected for name, expected in case["expect"].items()}
    return CaseResult(case["id"], case.get("lang", "?"), all(fields.values()), bool(case.get("known_gap")), fields, got)


def run(cases: list[dict] | None = None) -> Score:
    score = Score()
    for case in cases if cases is not None else load_cases():
        result = grade(case)
        score.total += 1
        score.by_lang[result.lang][1] += 1
        for name, correct in result.fields.items():
            score.by_field[name][1] += 1
            score.by_field[name][0] += int(correct)
        if result.passed:
            score.passed += 1
            score.by_lang[result.lang][0] += 1
            if result.known_gap:
                score.known_gaps_fixed.append(result.case_id)
        else:
            score.failures.append(result)
    return score


def format_report(score: Score) -> str:
    lines = [f"understanding benchmark: {score.passed}/{score.total} cases ({score.accuracy:.1%})", "", "by field:"]
    for name, (ok, graded) in sorted(score.by_field.items()):
        lines.append(f"  {name:<11} {ok:>4}/{graded:<4} {ok / graded:.1%}")
    lines += ["", "by language:"]
    for name, (ok, total) in sorted(score.by_lang.items()):
        lines.append(f"  {name:<3} {ok:>4}/{total:<4} {ok / total:.1%}")
    unexpected = [item for item in score.failures if not item.known_gap]
    known = [item for item in score.failures if item.known_gap]
    if unexpected:
        lines += ["", "unexpected failures:"]
        lines += [f"  {item.case_id}: wrong {', '.join(k for k, v in item.fields.items() if not v)} -> {item.got}" for item in unexpected]
    if known:
        lines += ["", f"known gaps still open: {len(known)}"]
    if score.known_gaps_fixed:
        lines += ["", "known gaps now answered correctly (remove the known_gap mark): " + ", ".join(score.known_gaps_fixed)]
    return "\n".join(lines)
