"""Does a message continue the previous question?

A follow-up is a short message that changes one detail of the phone asked
about before ("那 512 呢？", "白は？", "how about Hong Kong?") instead of
naming a phone itself.  This module only looks at the wording; deciding which
phone is meant is history.py's job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai_gateway.understanding.normalize import normalize_query

# words that point back at the previous question
FOLLOW_UP_CUES: tuple[str, ...] = (
    # Chinese
    "那", "那么", "那个", "呢", "这个", "它", "同样", "还有", "换成", "如果是",
    # Japanese
    "それ", "その", "じゃあ", "では", "なら", "だと", "だったら", "の場合", "同じ", "こっち", "そっち", "も",
    # English
    "what about", "how about", "and the", "and in", "same for", "that one", "it", "instead",
)

# a message this short that names no phone is almost always a follow-up
SHORT_MESSAGE_CHARS = 14
# longer than this, a message is a question of its own even with a cue word ("…今売るなら…")
LONG_MESSAGE_CHARS = 40

# phrases that start a new topic even when they are short
NEW_TOPIC_CUES: tuple[str, ...] = (
    "こんにちは", "ありがとう", "你好", "谢谢", "hello", "thanks", "thank you", "iphoneの種類", "有哪些型号",
)


@dataclass
class FollowUpSignal:
    is_follow_up: bool
    cues: list[str] = field(default_factory=list)  # cue words found
    short: bool = False  # the message is short enough to be a follow-up on its own


def _has_cue(text: str, cue: str) -> bool:
    if cue.isascii():
        return re.search(rf"(?<![a-z]){re.escape(cue)}(?![a-z])", text) is not None
    return cue in text


def follow_up_signal(message: str) -> FollowUpSignal:
    """Wording-level guess; the caller still requires that the message names no phone."""
    text = normalize_query(message)
    if not text:
        return FollowUpSignal(False)
    if any(_has_cue(text, cue) for cue in NEW_TOPIC_CUES):
        return FollowUpSignal(False)
    length = len(text.replace(" ", ""))
    if length > LONG_MESSAGE_CHARS:
        return FollowUpSignal(False)
    cues = [cue for cue in FOLLOW_UP_CUES if _has_cue(text, cue)]
    short = length <= SHORT_MESSAGE_CHARS
    return FollowUpSignal(bool(cues) or short, cues, short)
