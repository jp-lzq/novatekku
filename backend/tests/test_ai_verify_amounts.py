"""Finding money amounts in answer text."""

import pytest

from app.ai_gateway.verify.amounts import find_amounts


def amounts(text):
    return [(a.value, a.currency) for a in find_amounts(text)]


@pytest.mark.parametrize("text,expected", [
    ("最高は ¥208,000 です", [(208000, "JPY")]),
    ("最高は ￥208000", [(208000, "JPY")]),
    ("208,000円で買取", [(208000, "JPY")]),
    ("208000 円", [(208000, "JPY")]),
    ("約20.8万円です", [(208000, "JPY")]),
    ("20万8千円", [(208000, "JPY")]),
    ("20万8000円", [(208000, "JPY")]),
    ("20万円前後", [(200000, "JPY")]),
    ("回收价 175,500日元", [(175500, "JPY")]),
    ("HK$10,800", [(10800, "HKD")]),
    ("港币10800", [(10800, "HKD")]),
    ("10,800港元", [(10800, "HKD")]),
    ("$1,531", [(1531, "USD")]),
    ("US$1,531", [(1531, "USD")]),
    ("1,531美元", [(1531, "USD")]),
    ("USD 1,531", [(1531, "USD")]),
])
def test_spellings(text, expected):
    assert amounts(text) == expected


@pytest.mark.parametrize("text", [
    "iPhone 17 Pro 256GB", "3.4% 上昇", "18店", "20万件のデータ", "2026年11月", "5G 対応", "x2 台",
])
def test_not_amounts(text):
    assert amounts(text) == []


def test_several_amounts_in_order():
    text = "森森買取は208,000円、アキモバは¥206,000、香港は HK$10,800 です。"
    assert amounts(text) == [(208000, "JPY"), (206000, "JPY"), (10800, "HKD")]


def test_full_width_digits():
    assert amounts("２０８，０００円") == [(208000, "JPY")]


@pytest.mark.parametrize("text,approximate", [
    ("約20.8万円", True), ("约 208,000日元", True), ("about ¥208,000", True), ("20万円前後", True),
    ("~¥208,000", True), ("208,000円", False),
])
def test_approximate_marks(text, approximate):
    assert find_amounts(text)[0].approximate is approximate


def test_positions_point_at_the_text():
    text = "最高は208,000円です"
    amount = find_amounts(text)[0]
    assert text[amount.start:amount.end] == "208,000円"
