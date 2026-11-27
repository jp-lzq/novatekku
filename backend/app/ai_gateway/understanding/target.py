"""Recognise a target price: "20万円以上で売れる？" / "能卖到18万吗" / "can I get 200,000 yen for it".

``target_price`` returns the yen amount a seller hopes to get, or None.  Only
amounts written as money count (万 / 萬 / 円 / ¥ / yen / k / a comma-grouped
number), so capacities ("256") and model numbers ("17") are never read as a
target.  ``asks_target`` tells whether the wording asks if that amount can be
reached; an amount alone ("17 pro と 16e の差は8万円") is not a target question.
"""

from __future__ import annotations

import re
import unicodedata

MIN_TARGET = 10_000
MAX_TARGET = 3_000_000

_YEN = r"(?:円|日元|日圓|yen|jpy)"
# order matters: the first pattern that matches a span wins
_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(rf"(?<![\d.])(\d+(?:\.\d+)?)\s*[万萬](?:\s*(\d)\s*千)?\s*{_YEN}?"), "man"),
    (re.compile(r"[¥￥]\s*(\d{1,3}(?:,\d{3})+|\d+)(?![\d,])"), "plain"),
    (re.compile(rf"(?<![\d,.])(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*{_YEN}"), "plain"),
    (re.compile(r"(?<![\d,.])(\d{2,4}(?:\.\d)?)\s*k(?![a-z])"), "thousand"),
    (re.compile(r"(?<![\d,.])(\d{1,3}(?:,\d{3})+)(?![\d,])"), "plain"),
)

TARGET_CUES = re.compile(
    r"以上|超え|超す|越え|届[くかきけ]|いけ|行け|売れ|になる|なる(?:か|$)|もらえ|つく|付く|狙え|可能"
    r"|能卖|卖到|卖得到|卖得了|到不到|达到|超过|能不能|能到|有没有|可以卖|值不值"
    r"|\b(?:can i get|could i get|get .{0,24}for|at least|over|more than|above|reach(?:es)?|sell (?:it |this |them )?for|fetch|possible)\b"
)


def _value(match: re.Match, kind: str) -> int:
    number = float(match.group(1).replace(",", ""))
    if kind == "man":
        number = number * 10_000 + (int(match.group(2)) * 1_000 if match.group(2) else 0)
    elif kind == "thousand":
        number *= 1_000
    return int(round(number))


def find_target_amounts(message: str) -> list[int]:
    """Every money amount in the message, in reading order (yen)."""
    text = unicodedata.normalize("NFKC", str(message or "")).lower()
    found: list[tuple[int, int]] = []
    taken: list[tuple[int, int]] = []
    for pattern, kind in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < t_end and end > t_start for t_start, t_end in taken):
                continue
            taken.append((start, end))
            value = _value(match, kind)
            if MIN_TARGET <= value <= MAX_TARGET:
                found.append((start, value))
    return [value for _, value in sorted(found)]


def target_price(message: str) -> int | None:
    """The first money amount in the message; a target is a single amount, the first one is the one asked about."""
    amounts = find_target_amounts(message)
    return amounts[0] if amounts else None


def asks_target(text: str) -> list[str]:
    """Cue words that ask whether an amount can be reached; ``text`` is normalize_query() output."""
    return [match.group(0) for match in TARGET_CUES.finditer(text)][:3]
