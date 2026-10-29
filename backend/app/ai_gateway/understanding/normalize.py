"""Spelling normalisation applied before any recognition.

Users type the same thing in many ways: full-width digits, Chinese or kanji
numbers, katakana brand names, "1テラ" for 1TB, "256G" for 256GB.  This module
rewrites a question into one lower-case form so the recognisers only need to
handle a single spelling.  It never drops information that matters, it only
changes how it is written.
"""

from __future__ import annotations

import re
import unicodedata

# Chinese / Japanese digits used in numbers such as 十七 (17) or 二十 (20).
_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "两": 2, "兩": 2, "三": 3, "四": 4,
           "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_KANJI_NUMBER = re.compile(r"[一二两兩三四五六七八九]?十[一二三四五六七八九]?|[〇零一二两兩三四五六七八九]")

# Brand spellings that all mean "iphone".
_IPHONE_SPELLINGS = (
    "アイフォーン", "アイフォン", "あいふぉん", "ｉｐｈｏｎｅ", "i phone", "i-phone",
    "苹果手机", "蘋果手機", "愛瘋", "爱疯",
)

# Size words that mean a storage unit.
_GB_WORDS = ("ギガバイト", "ギガ", "gigabytes", "gigabyte", "千兆", "g字节")
_TB_WORDS = ("テラバイト", "テラ", "terabytes", "terabyte", "t字节")


def kanji_to_int(token: str) -> int | None:
    """Value of a Chinese/Japanese number up to 99 ("十七" -> 17, "二十" -> 20, "七" -> 7)."""
    if not token:
        return None
    if "十" not in token:
        return _DIGITS.get(token) if len(token) == 1 else None
    tens_part, _, ones_part = token.partition("十")
    tens = _DIGITS.get(tens_part, None) if tens_part else 1
    ones = _DIGITS.get(ones_part, None) if ones_part else 0
    if tens is None or ones is None:
        return None
    return tens * 10 + ones


def _replace_kanji_numbers(text: str) -> str:
    """Rewrite kanji numbers that sit next to a model or a counter word.

    Only numbers followed by a variant/unit or preceded by "iphone" are
    rewritten, so ordinary words such as 一番 (best) or 一緒 stay intact.
    """
    context_after = r"(?=\s*(?:pro|プロ|max|マックス|ppm|pm|plus|プラス|mini|ミニ|air|エア|e\b|台|部|个|個|件|代|系列|シリーズ|gb|tb|号|号机))"
    context_before = r"(?<=iphone)\s*"

    def replace(match: re.Match) -> str:
        value = kanji_to_int(match.group(0).strip())
        return str(value) if value is not None else match.group(0)

    text = re.sub(context_before + f"(?:{_KANJI_NUMBER.pattern})", lambda m: " " + replace(m), text)
    text = re.sub(f"(?:{_KANJI_NUMBER.pattern}){context_after}", replace, text)
    return text


def normalize_query(text: str) -> str:
    """Lower-case, half-width, one spelling per concept, single spaces."""
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.lower()
    for spelling in _IPHONE_SPELLINGS:
        text = text.replace(unicodedata.normalize("NFKC", spelling).lower(), "iphone")
    text = _replace_kanji_numbers(text)
    for word in _TB_WORDS:
        text = text.replace(word, "tb")
    for word in _GB_WORDS:
        text = text.replace(word, "gb")
    # "256g" / "256 g" / "1t" -> "256gb" / "1tb"; only real iPhone sizes, so "5g" (network) stays
    text = re.sub(r"(?<!\d)(64|128|256|512)\s*g(?![a-z])", r"\1gb", text)
    text = re.sub(r"(?<!\d)([12])\s*t(?![a-z])", r"\1tb", text)
    text = re.sub(r"(\d)\s*(gb|tb)\b", r"\1\2", text)
    # quantities: "16e×3" / "256x2" -> "16e x3" / "256 x2" so the model and the count stay separate
    text = text.replace("×", " x").replace("＊", "*")
    # "4x 17 pro" / "4x iphone 16e": a count written before the model -> "4台 17 pro"
    text = re.sub(r"(?<![\d.])(\d{1,3})\s*x\s+(?=iphone|\d{2}(?!\d))", r"\1台 ", text)
    text = re.sub(r"(?<=\d|b|e)\s*([x*])\s*(?=\d)", r" \1", text)
    text = re.sub(r"[、，,。．!！?？「」『』（）()【】\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact(text: str) -> str:
    """normalize_query without spaces or separators, for alias lookups."""
    return re.sub(r"[\s\-_/・.]", "", normalize_query(text))
