"""Recognise which iPhone(s) a question is about.

``extract_devices`` turns free text such as "17プロマ 256 白 未開封 2台" or
"十六pm 1t 和 15 pro 哪个值钱" into one ``DeviceMention`` per phone: model,
capacity, colour, condition, carrier and quantity.  Capacities, colours and
conditions written after a model belong to that model until the next model
starts.  Everything is rule-based and explainable: each field records the
text it came from.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from app.pricing.product_catalog import STANDARD_MODEL_COLORS, infer_color_code

from .lexicon import (
    CAPACITIES_GB,
    CARRIER_ALIASES,
    CONDITION_ALIASES,
    DUO_ALIASES,
    DUO_GENERIC,
    DURATION_AFTER,
    MAX_GENERATION,
    MIN_GENERATION,
    NOT_IPHONE_BEFORE,
    OTHER_MAKERS,
    QUANTITY_COUNTERS,
    UNNUMBERED_MODELS,
    VARIANT_ALIASES,
)
from .normalize import normalize_query

KNOWN_MODELS: frozenset[str] = frozenset(STANDARD_MODEL_COLORS)


@dataclass
class DeviceMention:
    model: str  # canonical name, e.g. "iPhone 17 Pro Max"; may be unknown to the catalogue
    generation: int | None
    variant: str | None  # "Pro Max", "Pro", "Plus", "mini", "Air", "e" or None for the base model
    capacity: str | None = None  # "256", "1TB" (same spelling as products.capacity)
    color: str | None = None  # catalogue colour code, e.g. "deep-blue"
    condition: str | None = None  # sealed / new / opened / used / broken
    carrier: str | None = None  # sim_free / docomo / au / softbank / rakuten / hk_model / ...
    quantity: int = 1
    known: bool = True  # the model exists in NOVA's catalogue
    evidence: dict[str, str] = field(default_factory=dict)  # field -> text it was read from
    start: int = 0
    end: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("start")
        data.pop("end")
        return data


def _variant_pattern() -> str:
    words = sorted({re.escape(alias) for alias, _ in VARIANT_ALIASES}, key=len, reverse=True)
    return "|".join(words)


_VARIANT_LOOKUP = {alias: name for alias, name in VARIANT_ALIASES}
_MODEL_RE = re.compile(
    rf"(?:iphone\s*)?(?<!\d)(\d{{2}})(?!\d)\s*({_variant_pattern()})?(?![a-z])",
)
_COUNTER = "|".join(map(re.escape, QUANTITY_COUNTERS))
_DUO_RE = re.compile("|".join(re.escape(alias) for alias in sorted(DUO_ALIASES, key=len, reverse=True)))
_CAPACITY_RE = re.compile(r"(?<!\d)(64|128|256|512|1024|2048)\s*(?:gb)?(?![\d])|(?<!\d)([12])\s*tb(?![a-z])")
_QUANTITY_RE = re.compile(
    rf"(?:(?<![a-z])[x*]\s*(\d{{1,3}})(?!\d))|(?<![\d.])(\d{{1,3}})\s*(?:{_COUNTER})(?!\s*{DURATION_AFTER})"
)
# "两台17pro": a count written right before a model
_PREFIX_QUANTITY_RE = re.compile(rf"(?<![\d.])(\d{{1,3}})\s*(?:{_COUNTER})\s*(?:的\s*)?$")
_NOT_IPHONE_RE = re.compile(NOT_IPHONE_BEFORE)


def model_name(generation: int | None, variant: str | None) -> str:
    if generation is None:
        return "iPhone Duo"
    if variant == "e":
        return f"iPhone {generation}e"
    return f"iPhone {generation}" + (f" {variant}" if variant else "")


def capacity_label(gigabytes: int) -> str:
    return f"{gigabytes // 1024}TB" if gigabytes >= 1024 else str(gigabytes)


def _model_spans(text: str) -> list[tuple[int, int, int | None, str | None, str]]:
    spans: list[tuple[int, int, int | None, str | None, str]] = []
    for match in _MODEL_RE.finditer(text):
        generation = int(match.group(1))
        if not MIN_GENERATION <= generation <= MAX_GENERATION:
            continue
        has_iphone = "iphone" in match.group(0)
        number_start = match.start(1)
        if _part_of_other_number(text, number_start, match.end(1)):
            continue
        before = text[max(0, number_start - 16):number_start]
        if not has_iphone:
            # "a18 pro", "m4", "s24": a letter glued to the number names something else
            if number_start and text[number_start - 1].isascii() and text[number_start - 1].isalpha():
                continue
            if _NOT_IPHONE_RE.search(before):
                continue
        # a bare number right before a size, counter, unit or money is not a model ("12台", "17万円")
        tail = text[match.end(1):match.end(1) + 3]
        if not match.group(2) and re.match(r"\s*(gb|tb|台|部|个|個|件|円|万|元|年|月|日|時|点|分|%|歳|岁|inch|インチ|cm|mm|kg)", tail):
            continue
        variant_word = (match.group(2) or "").strip()
        variant = _VARIANT_LOOKUP.get(variant_word) if variant_word else None
        if variant_word in ("pm", "ppm") and generation <= 12:
            continue  # "11 pm", "12pm" are times of day
        if not has_iphone and not variant_word and not _looks_like_model_context(text, match.start(), match.end()):
            continue
        spans.append((match.start(), match.end(), generation, variant, match.group(0).strip()))
    taken = lambda position: any(start <= position < end for start, end, *_ in spans)  # noqa: E731
    for alias, name in UNNUMBERED_MODELS:
        for match in re.finditer(re.escape(alias), text):
            if not taken(match.start()):
                spans.append((match.start(), match.end(), 17, "Air", match.group(0)))
    other_maker = any(maker in text for maker in OTHER_MAKERS)
    for match in _DUO_RE.finditer(text):
        if taken(match.start()):
            continue
        if match.group(0) in DUO_GENERIC and other_maker:
            continue  # "galaxy z fold" is not the iPhone foldable
        spans.append((match.start(), match.end(), None, None, match.group(0)))
    spans.sort()
    return spans


_CAPACITY_AFTER_SLASH = re.compile(r"/\s*(?:64|128|256|512|1024|2048|[12]\s*tb)")


def _part_of_other_number(text: str, start: int, end: int) -> bool:
    """True for "12.5万", "15:00", "11/15", "1,280" — but not "iphone 16." or "17/256gb"."""
    before = text[max(0, start - 3):start]
    after = text[end:end + 4]
    if re.match(r"[.,:]\d", after) or re.search(r"\d[.,:]$", before):
        return True
    if after.startswith("/") or before.endswith("/"):
        if _CAPACITY_AFTER_SLASH.match(text, end):
            return False  # "17/256gb"
        value = int(text[start:end])
        left = re.search(r"(\d{1,2})\s*/\s*$", before)
        right = re.match(r"/\s*(\d{1,2})(?!\d)", after)
        # a date is month/day: "11/15", "3/17"; "15/16" (two models) is not
        if right and value <= 12 and int(right.group(1)) <= 31:
            return True
        if left and int(left.group(1)) <= 12 and value <= 31:
            return True
    return False


def _looks_like_model_context(text: str, start: int, end: int) -> bool:
    """A bare "17" counts as a model only near phone words or a capacity ("17 256", "16 売りたい")."""
    window = text[max(0, start - 12):end + 16]
    if re.search(r"iphone|アイフォン|機種|机型|型号|モデル|model|買取|回收|売|卖|値段|价格|price|sell", window):
        return True
    after = text[end:end + 10]
    if re.match(rf"\s*(?:[x*]\s*\d|\d{{1,3}}\s*(?:{_COUNTER}))", after):
        return True  # "17 x2", "17 2台"
    if _PREFIX_QUANTITY_RE.search(text[max(0, start - 8):start]):
        return True  # "2台17"
    return bool(_CAPACITY_RE.search(after))


def _lookup(text: str, aliases: tuple[tuple[str, str], ...]) -> tuple[str, str] | None:
    for alias, value in aliases:
        if alias.isascii():
            if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", text):
                return value, alias
        elif alias in text:
            return value, alias
    return None


def _capacity_in(text: str) -> tuple[str, str] | None:
    match = _CAPACITY_RE.search(text)
    if not match:
        return None
    gigabytes = int(match.group(1)) if match.group(1) else int(match.group(2)) * 1024
    if gigabytes not in CAPACITIES_GB:
        return None
    return capacity_label(gigabytes), match.group(0).strip()


def _quantity_in(text: str) -> tuple[int, str] | None:
    match = _QUANTITY_RE.search(text)
    if not match:
        return None
    value = int(match.group(1) or match.group(2))
    if not 1 <= value <= 999:
        return None
    return value, match.group(0).strip()


def extract_devices(message: str) -> list[DeviceMention]:
    """Every phone mentioned in the message, in the order written."""
    text = normalize_query(message)
    spans = _model_spans(text)
    devices: list[DeviceMention] = []
    # a count written just before a model belongs to that model, not to the previous one
    # ("16e 3台 17 2台": the 3台 stays with 16e because 17 has its own count)
    prefix = {}
    for index, (start, end, *_rest) in enumerate(spans):
        found = _PREFIX_QUANTITY_RE.search(text[(spans[index - 1][1] if index else 0):start])
        own_end = spans[index + 1][0] if index + 1 < len(spans) else len(text)
        if found and not (index and _QUANTITY_RE.search(text[end:own_end])):
            prefix[index] = found
    for index, (start, end, generation, variant, raw) in enumerate(spans):
        segment_end = spans[index + 1][0] if index + 1 < len(spans) else len(text)
        next_prefix = prefix.get(index + 1)
        if next_prefix:
            segment_end = end + next_prefix.start()
        segment = text[end:max(end, segment_end)]
        name = model_name(generation, variant)
        device = DeviceMention(
            model=name,
            generation=generation,
            variant=variant if generation is not None else "Duo",
            known=name in KNOWN_MODELS,
            evidence={"model": raw},
            start=start,
            end=segment_end,
        )
        if (found := _capacity_in(segment)):
            device.capacity, device.evidence["capacity"] = found
        if (found := _lookup(segment, CONDITION_ALIASES)):
            device.condition, device.evidence["condition"] = found
        if (found := _lookup(segment, CARRIER_ALIASES)):
            device.carrier, device.evidence["carrier"] = found
        if prefix.get(index):
            device.quantity = int(prefix[index].group(1))
            device.evidence["quantity"] = prefix[index].group(0).strip()
        elif (found := _quantity_in(segment)):
            device.quantity, device.evidence["quantity"] = found
        color = infer_color_code(name, segment) if device.known else None
        if color:
            device.color = color
            device.evidence["color"] = color
        devices.append(device)
    return _merge_repeats(devices)


def _merge_repeats(devices: list[DeviceMention]) -> list[DeviceMention]:
    """"17 pro 256 ... 17 pro 512" stays two mentions; an exact repeat without new facts is dropped."""
    result: list[DeviceMention] = []
    for device in devices:
        previous = next((item for item in result if item.model == device.model), None)
        if previous and device.capacity in (None, previous.capacity) and not device.color and not device.condition:
            continue
        result.append(device)
    return result


def capacity_without_model(message: str) -> str | None:
    """A capacity asked on its own, e.g. the follow-up "那 512 呢？"."""
    text = normalize_query(message)
    if _model_spans(text):
        return None
    found = _capacity_in(text)
    return found[0] if found else None
