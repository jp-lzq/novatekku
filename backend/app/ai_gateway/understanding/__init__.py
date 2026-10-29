"""Question understanding for NOVA AI: what is asked, and about which iPhones.

    from app.ai_gateway.understanding import understand
    result = understand("17プロマ 256 白 未開封 2台 どこが一番高い？")
    result.intent.intent      -> "store_ranking"
    result.devices[0].model   -> "iPhone 17 Pro Max"

The result is attached to every AIRequest so the AI core can choose how to
answer.  Nothing here calls a model or the network; it is fast enough to run
on every message.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .entities import DeviceMention, capacity_without_model, extract_devices
from .intents import IntentResult, classify
from .normalize import normalize_query

__all__ = ["Understanding", "understand", "DeviceMention", "IntentResult"]

VERSION = "understanding-v1"


@dataclass
class Understanding:
    text: str  # normalised question
    intent: IntentResult
    devices: list[DeviceMention] = field(default_factory=list)
    follow_up_capacity: str | None = None  # "那 512 呢？": a capacity without a model
    unknown_models: list[str] = field(default_factory=list)  # e.g. "iPhone 12" (not in NOVA's catalogue)

    def to_dict(self) -> dict:
        return {
            "version": VERSION,
            "text": self.text,
            **self.intent.to_dict(),
            "devices": [device.to_dict() for device in self.devices],
            "follow_up_capacity": self.follow_up_capacity,
            "unknown_models": self.unknown_models,
        }


def understand(message: str) -> Understanding:
    text = normalize_query(message)
    devices = extract_devices(message)
    follow_up_capacity = capacity_without_model(message)
    return Understanding(
        text=text,
        intent=classify(text, devices, follow_up=follow_up_capacity is not None),
        devices=devices,
        follow_up_capacity=follow_up_capacity,
        unknown_models=[device.model for device in devices if not device.known],
    )
