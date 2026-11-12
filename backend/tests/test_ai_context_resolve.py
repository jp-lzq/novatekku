"""Resolving follow-ups against the conversation, and the effect on the AI request."""

import pytest

from app.ai_gateway.context import resolve, resolve_message
from app.ai_gateway.context.history import topic_from_history, user_messages
from app.ai_gateway.understanding import intents as I


def turns(*messages):
    history = []
    for message in messages:
        history += [{"role": "user", "content": message},
                    {"role": "assistant", "content": "iPhone 16 Pro 128GB は 100,000円、iPhone 15 は 60,000円です"}]
    return history


def summary(message, *earlier):
    result = resolve(message, turns(*earlier)).to_dict()
    return result["intent"], [(d["model"], d["capacity"], d["color"], d["quantity"]) for d in result["devices"]]


def test_capacity_follow_up():
    assert summary("512 は？", "iPhone 17 Pro 256 はいくら？") == (I.PRICE_QUOTE, [("iPhone 17 Pro", "512", None, 1)])


def test_chain_keeps_the_latest_change():
    intent, devices = summary("白は？", "iPhone 17 Pro 256 はいくら？", "512 は？")
    assert devices == [("iPhone 17 Pro", "512", "silver", 1)]


def test_market_follow_up_becomes_overseas():
    result = resolve("香港なら？", turns("iPhone 17 Pro 256 はいくら？")).to_dict()
    assert result["intent"] == I.OVERSEAS_MARKET
    assert result["markets"] == ["hk"]
    assert result["devices"][0]["model"] == "iPhone 17 Pro"


def test_english_and_chinese():
    assert summary("what about 256?", "how much is iphone 16e 128")[1] == [("iPhone 16e", "256", None, 1)]
    assert summary("那 256 呢？", "17 pro max 1tb 多少钱")[1] == [("iPhone 17 Pro Max", "256", None, 1)]
    assert resolve("and in the US?", turns("how much is iphone 16e 128")).to_dict()["markets"] == ["us"]


def test_comparison_stays_a_comparison():
    intent, devices = summary("512 だと？", "17 pro と 16 pro はどっちが高い？")
    assert intent == I.MODEL_COMPARE
    assert [d[1] for d in devices] == ["512", "512"]


def test_quantity_follow_up_and_carried_fields():
    result = resolve("2台だと？", turns("iPhone 17 Pro 256 白はいくら？")).to_dict()
    assert result["devices"][0]["quantity"] == 2
    assert result["context"]["carried"] == {"iPhone 17 Pro": ["capacity", "color"]}
    assert result["context"]["turns_ago"] == 1


def test_question_naming_its_own_phone_is_unchanged():
    result = resolve("iPhone 16 128 は？", turns("17 pro 256 いくら")).to_dict()
    assert result["context"]["follow_up"] is False
    assert [d["model"] for d in result["devices"]] == ["iPhone 16"]


@pytest.mark.parametrize("message", ["ビットコインの価格は？", "今日の天気は？", "ありがとう", "こんにちは"])
def test_unrelated_short_messages_are_not_follow_ups(message):
    result = resolve(message, turns("17 pro 256 いくら")).to_dict()
    assert result["context"]["follow_up"] is False
    assert result["devices"] == []


def test_no_history_means_no_follow_up():
    result = resolve("512 は？", []).to_dict()
    assert result["devices"] == [] and result["follow_up_capacity"] == "512"


def test_greeting_in_between_does_not_break_the_chain():
    assert summary("512 は？", "17 pro 256 いくら", "ありがとう")[1] == [("iPhone 17 Pro", "512", None, 1)]


def test_assistant_messages_are_ignored():
    history = [{"role": "assistant", "content": "iPhone 15 Pro 128GB の価格です"}]
    assert resolve("512 は？", history).devices == []
    assert user_messages(history) == []


def test_only_recent_messages_are_used():
    old = ["iPhone 15 128 いくら"] + ["ありがとう"] * 4
    assert topic_from_history(turns(*old)) is None


def test_malformed_history_is_ignored():
    history = [None, "text", {"role": "user"}, {"role": "user", "content": "17 pro 256 いくら"}]
    assert summary("512 は？")[1] == []
    assert resolve("512 は？", history).devices[0]["capacity"] == "512"


def test_resolve_message_is_json_ready():
    import json

    data = resolve_message("512 は？", turns("17 pro 256 いくら"))
    json.dumps(data, ensure_ascii=False)
    assert data["context"]["version"] == "context-v1"
    assert data["needs_prices"] is True
