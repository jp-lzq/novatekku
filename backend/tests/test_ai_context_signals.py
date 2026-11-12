"""Wording-level detection of follow-up questions."""

import pytest

from app.ai_gateway.context.signals import follow_up_signal


@pytest.mark.parametrize("message", [
    "那 512 呢？", "512 は？", "白は？", "香港なら？", "2台だと？", "what about 256?", "how about the white one",
    "それはいくら？", "じゃあ1TBは", "和16比呢", "same for the 512",
])
def test_follow_ups(message):
    assert follow_up_signal(message).is_follow_up


@pytest.mark.parametrize("message", [
    "こんにちは", "ありがとう", "你好", "thanks!", "hello",
    "iPhone 17 Pro と 16 Pro Max を比べて、今売るならどちらが高く売れるか教えてください",
])
def test_not_follow_ups(message):
    assert not follow_up_signal(message).is_follow_up


def test_cues_are_reported():
    signal = follow_up_signal("那 512 呢？")
    assert "那" in signal.cues and "呢" in signal.cues
    assert signal.short


def test_english_cues_need_word_boundaries():
    assert "it" not in follow_up_signal("iPhone with a big battery").cues
    assert "it" in follow_up_signal("how much is it in hong kong").cues


def test_empty_message():
    assert not follow_up_signal("").is_follow_up
    assert not follow_up_signal("   ").is_follow_up
