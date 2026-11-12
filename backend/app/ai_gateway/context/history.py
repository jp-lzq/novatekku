"""Find the phone that the earlier part of the conversation was about.

Only the user's own messages are read (the assistant may list many models in
an answer).  The messages are replayed oldest first, each one resolved against
the topic so far, so a chain such as "17 Pro 256 は？" → "512 は？" → "白は？"
ends on the 17 Pro 512 in white rather than jumping back to the 256.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# how many earlier user messages are replayed
LOOKBACK_USER_MESSAGES = 4


@dataclass
class Topic:
    devices: list[dict]  # device dicts as in Understanding.to_dict()["devices"]
    markets: list[str] = field(default_factory=list)
    turns_ago: int = 0  # 1 = set by the user's previous message
    intent: str | None = None  # what kind of question the topic came from


def user_messages(history: list[dict]) -> list[str]:
    """Earlier user messages, oldest first."""
    return [
        str(item.get("content") or "")
        for item in history or []
        if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
    ]


def topic_from_history(history: list[dict]) -> Topic | None:
    """Replay the last few user messages and return the phone they ended on."""
    from . import resolve  # local import: resolve() uses this module too

    messages = user_messages(history)[-LOOKBACK_USER_MESSAGES:]
    topic: Topic | None = None
    for index, message in enumerate(messages):
        resolved = resolve(message, topic=topic)
        if resolved.devices:
            topic = Topic(
                devices=resolved.devices,
                markets=resolved.markets,
                turns_ago=len(messages) - index,
                intent=resolved.understanding.get("intent"),
            )
    return topic
