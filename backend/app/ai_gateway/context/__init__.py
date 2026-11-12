"""Conversation context for NOVA AI: carry the phone from one question to the next.

    resolve("那 512 呢？", history)
    -> devices = [iPhone 17 Pro, 512] when the previous user message was "17 Pro 256 多少钱"

``resolve`` returns the same shape as ``understanding.understand(...).to_dict()``
plus a ``context`` block, so it can replace the plain understanding in the AI
request.  A message that names its own phone is never changed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai_gateway.understanding import understand
from app.ai_gateway.understanding import intents as I

from .history import Topic, topic_from_history
from .merge import apply_follow_up, follow_up_details
from .signals import follow_up_signal

__all__ = ["Resolved", "resolve", "resolve_message"]

VERSION = "context-v1"

# intents that keep the earlier question's intent when the follow-up has no clear one of its own
INHERITABLE_INTENTS = frozenset(I.PRICE_INTENTS | {I.RETAIL_PRICE, I.CATALOG})


@dataclass
class Resolved:
    understanding: dict  # understand(...).to_dict(), with devices filled in for follow-ups
    devices: list[dict] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)
    follow_up: bool = False
    carried: dict[str, list[str]] = field(default_factory=dict)  # model -> fields taken from history
    turns_ago: int | None = None

    def to_dict(self) -> dict:
        return {
            **self.understanding,
            "devices": self.devices,
            "markets": self.markets,
            "context": {
                "version": VERSION,
                "follow_up": self.follow_up,
                "carried": self.carried,
                "turns_ago": self.turns_ago,
            },
        }


def resolve(message: str, history: list[dict] | None = None, *, topic: Topic | None = None) -> Resolved:
    """Understand ``message`` in the context of the earlier user messages."""
    current = understand(message).to_dict()
    resolved = Resolved(understanding=current, devices=list(current["devices"]), markets=list(current["markets"]))
    if current["devices"]:
        return resolved  # names its own phone: nothing to carry
    signal = follow_up_signal(message)
    if not signal.is_follow_up or current["intent"] == I.GREETING:
        return resolved
    if topic is None:
        topic = topic_from_history(history or [])
    if topic is None:
        return resolved
    # A follow-up must change something ("512 は？", "白は？", "香港なら？") or point back
    # explicitly ("それはいくら？") while still being about phones.  "ビットコインの価格は？"
    # is short but neither, so it stays a question of its own.
    names_detail = bool(current["markets"]) or any(
        follow_up_details(message, device.get("model") or "") for device in topic.devices
    )
    points_back = bool(signal.cues) and current["intent"] != I.OFF_TOPIC
    if not (names_detail or points_back):
        return resolved

    devices, carried = apply_follow_up(topic.devices, message)
    resolved.devices = devices
    resolved.carried = carried
    resolved.follow_up = True
    resolved.turns_ago = topic.turns_ago
    resolved.markets = current["markets"] or topic.markets
    intent = current["intent"]
    own_cues = {name for name, found in (current.get("cues") or {}).items()
                if any(item != "follow-up capacity" for item in found)}
    if current["markets"] and any(market != "jp" for market in current["markets"]):
        intent = I.OVERSEAS_MARKET  # "香港なら？"
    elif not own_cues or intent in (I.OFF_TOPIC, I.DEVICE_HELP):
        # "512 だと？" says nothing about the kind of question: keep the earlier one
        intent = topic.intent if topic.intent in INHERITABLE_INTENTS else I.PRICE_QUOTE
    resolved.understanding = {**current, "intent": intent, "needs_prices": intent in I.PRICE_INTENTS}
    resolved.understanding["unknown_models"] = [d["model"] for d in devices if not d.get("known", True)]
    return resolved


def resolve_message(message: str, history: list[dict] | None = None) -> dict:
    """Convenience: the resolved understanding as a dict for AIRequest.understanding."""
    return resolve(message, history).to_dict()
