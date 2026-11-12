"""Find money amounts in an answer text.

Recognised spellings (yen unless a currency is written):
    ¥208,000  ￥208000  208,000円  208000 円  20.8万円  20万8千円  20万8000円  20万円
    HK$10,800  港币10800  10,800港元  $1,531  US$1,531  1,531美元  USD 1,531
Numbers that are capacities (256GB), percentages (3.4%), model names (iPhone 17)
or plain numbers without a currency are not amounts.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Amount:
    value: int  # in the currency below
    currency: str  # JPY / HKD / USD
    text: str  # as written
    start: int
    end: int
    approximate: bool = False  # written with 約 / 约 / about / ~ / 前後


_NUMBER = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?"
_MAN = r"(?P<man>\d+(?:\.\d+)?)\s*万(?:\s*(?P<sen>\d+)\s*千|\s*(?P<rest>\d{1,4}))?"
_APPROX_BEFORE = re.compile(r"(約|约|およそ|大约|大概|about|around|approximately|approx\.?|~|〜|～)\s*$", re.I)
_APPROX_AFTER = re.compile(r"^\s*(前後|程度|左右|ほど|くらい|ぐらい)")

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("HKD", re.compile(rf"(?:HK\$|HKD\s*|港币\s*|港幣\s*)(?P<num>{_NUMBER})", re.I)),
    ("HKD", re.compile(rf"(?P<num>{_NUMBER})\s*(?:港元|港币|港幣|香港ドル|HKD)", re.I)),
    ("USD", re.compile(rf"(?:US\$|USD\s*|(?<![A-Z])\$)(?P<num>{_NUMBER})", re.I)),
    ("USD", re.compile(rf"(?P<num>{_NUMBER})\s*(?:美元|美金|ドル|USD|dollars?)", re.I)),
    ("JPY", re.compile(rf"(?:[¥￥]|JPY\s*)(?P<num>{_NUMBER})(?!\s*万)", re.I)),
    ("JPY", re.compile(rf"(?:[¥￥]\s*)?{_MAN}\s*(?:円|日元|日圓|yen)?", re.I)),
    ("JPY", re.compile(rf"(?P<num>{_NUMBER})\s*(?:円|日元|日圓|yen|JPY)", re.I)),
]


def _to_int(number: str) -> int:
    return int(round(float(number.replace(",", ""))))


def _man_value(match: re.Match) -> int:
    value = float(match.group("man")) * 10000
    if match.group("sen"):
        value += int(match.group("sen")) * 1000
    elif match.group("rest"):
        value += int(match.group("rest"))
    return int(round(value))


def find_amounts(text: str) -> list[Amount]:
    """Every amount in reading order; overlapping spellings count once."""
    text = unicodedata.normalize("NFKC", str(text or ""))
    found: list[Amount] = []
    taken: list[tuple[int, int]] = []
    for currency, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < t_end and end > t_start for t_start, t_end in taken):
                continue
            if "man" in pattern.groupindex and match.group("man") is not None:
                if not re.search(r"円|日元|日圓|yen|[¥￥]", match.group(0), re.I):
                    continue  # "20万" without a currency could be a count ("20万件")
                value = _man_value(match)
            else:
                value = _to_int(match.group("num"))
            if value <= 0:
                continue
            approximate = bool(_APPROX_BEFORE.search(text[max(0, start - 14):start])) or bool(_APPROX_AFTER.match(text[end:end + 4]))
            found.append(Amount(value, currency, match.group(0).strip(), start, end, approximate))
            taken.append((start, end))
    return sorted(found, key=lambda amount: amount.start)
