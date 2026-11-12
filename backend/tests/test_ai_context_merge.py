"""Carrying a phone into a follow-up: only the named details change."""

import pytest

from app.ai_gateway.context.merge import apply_follow_up, follow_up_details

PRO = {"model": "iPhone 17 Pro", "generation": 17, "variant": "Pro", "capacity": "256", "color": "deep-blue",
       "condition": "sealed", "carrier": None, "quantity": 1, "known": True, "evidence": {"model": "17 pro"}}


@pytest.mark.parametrize("message,expected", [
    ("512 は？", {"capacity": "512"}),
    ("1T呢", {"capacity": "1TB"}),
    ("白は？", {"color": "silver"}),
    ("オレンジなら", {"color": "cosmic-orange"}),
    ("中古だと？", {"condition": "used"}),
    ("SIMフリーは", {"carrier": "sim_free"}),
    ("3台なら？", {"quantity": 3}),
    ("512 の白 2台", {"capacity": "512", "color": "silver", "quantity": 2}),
    ("それはいくら？", {}),
])
def test_details(message, expected):
    assert follow_up_details(message, "iPhone 17 Pro") == expected


def test_colour_must_exist_for_the_model():
    assert follow_up_details("ラベンダーは？", "iPhone 17 Pro") == {}  # lavender is an iPhone 17 colour only
    assert follow_up_details("ラベンダーは？", "iPhone 17") == {"color": "lavender"}


def test_only_named_fields_change_and_the_rest_is_carried():
    (device,), carried = apply_follow_up([PRO], "512 は？")
    assert device["model"] == "iPhone 17 Pro"
    assert device["capacity"] == "512"
    assert (device["color"], device["condition"]) == ("deep-blue", "sealed")
    assert device["evidence"]["capacity"] == "follow-up"
    assert device["evidence"]["model"] == "17 pro"
    assert carried == {"iPhone 17 Pro": ["color", "condition"]}


def test_earlier_device_is_not_modified_in_place():
    before = dict(PRO)
    apply_follow_up([PRO], "1TB は？")
    assert PRO == before


def test_change_applies_to_every_earlier_phone():
    other = {**PRO, "model": "iPhone 16 Pro", "capacity": None, "color": None}
    devices, _ = apply_follow_up([PRO, other], "512 だと？")
    assert [d["capacity"] for d in devices] == ["512", "512"]
