"""Understanding target-price questions and store-against-store questions."""

import pytest

from app.ai_gateway.context import resolve_message
from app.ai_gateway.understanding import understand
from app.ai_gateway.understanding.target import asks_target, find_target_amounts, target_price


@pytest.mark.parametrize("message, expected", [
    ("20万円以上で売れる？", 200000),
    ("能卖到18万吗", 180000),
    ("18萬可以卖吗", 180000),
    ("25.5万円超える？", 255000),
    ("20万5千円", 205000),
    ("can I get 200,000 yen for it", 200000),
    ("¥175,500 以上", 175500),
    ("￥180000 いける？", 180000),
    ("１８万円", 180000),  # full-width digits
    ("180k?", 180000),
    ("at least 230K", 230000),
    ("200,000 is fine?", 200000),
    ("9万日元", 90000),
])
def test_target_amount_spellings(message, expected):
    assert target_price(message) == expected


@pytest.mark.parametrize("message", [
    "17 pro 256 いくら",  # a capacity is not money
    "iPhone 17 Pro 512GB",
    "16e 128 x3",
    "5千円",  # too small to be a phone price
    "1,000 円",
    "12:30 に行けますか",
])
def test_numbers_that_are_not_targets(message):
    assert target_price(message) is None


def test_several_amounts_first_one_is_the_target():
    assert find_target_amounts("18万円か、せめて17万円") == [180000, 170000]
    assert target_price("18万円か、せめて17万円") == 180000


def test_target_cues_in_three_languages():
    assert asks_target("20万円以上で売れる")
    assert asks_target("能卖到18万吗")
    assert asks_target("can i get 200 000 yen for it")
    assert not asks_target("8万円の差")
    assert not asks_target("overseas price")  # "over" only as a word


@pytest.mark.parametrize("message, target", [
    ("17 Pro 256 は20万円以上で売れる？", 200000),
    ("17 pro 256 能卖到18万吗", 180000),
    ("can I get 200,000 yen for my iPhone 17 Pro 256GB?", 200000),
    ("17 pro 256 で 180k いける？", 180000),
    ("17pro 256 12.5万で売れる？", 125000),
])
def test_target_price_intent(message, target):
    result = understand(message).to_dict()
    assert result["intent"] == "target_price"
    assert result["target_price"] == target
    assert result["needs_prices"] is True
    assert result["devices"][0]["model"] == "iPhone 17 Pro"


def test_an_amount_without_a_target_question_keeps_its_intent():
    result = understand("17 pro と 16e の差は8万円くらい？").to_dict()
    assert result["intent"] == "model_compare"
    assert result["target_price"] == 80000  # read, but not asked as a target


def test_target_without_a_phone_is_not_off_topic():
    assert understand("20万円以上で売れる？").intent.intent == "target_price"


def test_target_follow_up_takes_the_earlier_phone():
    history = [{"role": "user", "content": "iPhone 17 Pro 512 はいくら？"}, {"role": "assistant", "content": "…"}]
    result = resolve_message("20万円以上で売れる？", history)
    assert result["intent"] == "target_price"
    assert [(device["model"], device["capacity"]) for device in result["devices"]] == [("iPhone 17 Pro", "512")]
    assert result["context"]["follow_up"] is True


@pytest.mark.parametrize("message", [
    "森森買取とアキモバ、17 Pro 256 はどっちが高い？",
    "17 pro 256 携帯空間和アキモバ哪家收得高",
    "which pays more for a 17 pro 256, アキモバ or 携帯空間?",
    "16e 128 は買取楽園とアキモバどちらが高く買い取ってくれる？",
])
def test_store_against_store_is_a_store_question(message):
    assert understand(message).intent.intent == "store_ranking"


@pytest.mark.parametrize("message, intent", [
    ("17 pro 256 と 512 どっちが高い？", "model_compare"),  # two capacities: still a comparison of phones
    ("17 pro と 16 pro max どっちが高く売れる？", "model_compare"),
    ("iPhone Duo 1TB 香港と日本どっちが高い？", "overseas_market"),
])
def test_comparisons_of_phones_and_markets_are_unchanged(message, intent):
    assert understand(message).intent.intent == intent
