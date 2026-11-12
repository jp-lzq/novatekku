"""Apply the details of a follow-up message to the phone asked about before.

The model always comes from the earlier question.  Capacity, colour,
condition, carrier, quantity and market are replaced only when the follow-up
names them; everything else is carried over.  A colour is accepted only if it
exists for that model (the catalogue decides, e.g. "白" is Silver on a 17 Pro).
"""

from __future__ import annotations

from app.ai_gateway.understanding.entities import _capacity_in, _lookup, _quantity_in
from app.ai_gateway.understanding.lexicon import CARRIER_ALIASES, CONDITION_ALIASES
from app.ai_gateway.understanding.normalize import normalize_query
from app.pricing.product_catalog import infer_color_code

CARRIED_FIELDS = ("capacity", "color", "condition", "carrier", "quantity")


def follow_up_details(message: str, model: str) -> dict:
    """The details a follow-up message sets for ``model`` (only the ones it names)."""
    text = normalize_query(message)
    details: dict = {}
    if (found := _capacity_in(text)):
        details["capacity"] = found[0]
    color = infer_color_code(model, text)
    if color:
        details["color"] = color
    if (found := _lookup(text, CONDITION_ALIASES)):
        details["condition"] = found[0]
    if (found := _lookup(text, CARRIER_ALIASES)):
        details["carrier"] = found[0]
    if (found := _quantity_in(text)):
        details["quantity"] = found[0]
    return details


def apply_follow_up(previous: list[dict], message: str) -> tuple[list[dict], dict[str, list[str]]]:
    """New device list and, per model, which fields came from the earlier question.

    With several earlier phones ("17 Pro と 16 Pro は？" → "512 は？") the
    change applies to all of them, because the follow-up does not single one out.
    """
    devices: list[dict] = []
    carried: dict[str, list[str]] = {}
    for device in previous:
        details = follow_up_details(message, device.get("model") or "")
        updated = {**device, **details}
        updated["evidence"] = {**(device.get("evidence") or {}), **{key: "follow-up" for key in details}}
        devices.append(updated)
        carried[updated["model"]] = [name for name in CARRIED_FIELDS if name not in details and device.get(name) not in (None, 1)]
    return devices, carried
