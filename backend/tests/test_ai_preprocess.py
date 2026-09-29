from app.ai_gateway import preprocess as ai


def test_local_price_context_is_only_added_when_needed():
    assert ai.requires_local_price_context("iPhone 17 Pro 256GB 现在多少钱？") is True
    assert ai.requires_local_price_context("哪家店铺回收价格最高？") is True
    assert ai.requires_local_price_context("Android 手机掉电很快怎么办？") is False
    assert ai.requires_local_price_context("How do I move photos to a new phone?") is False
    assert ai.requires_local_price_context(
        "如果卖两台一共多少钱？",
        [{"role": "user", "content": "iPhone 17 Pro Max 256GB 的价格"}],
    ) is True
    assert ai.requires_local_price_context("现在适合卖掉我的 iPhone 吗？") is True
    assert ai.requires_local_price_context("今はiPhoneを売る良いタイミングですか？") is True
    assert ai.requires_local_price_context("Is now a good time to sell my iPhone?") is True


ROWS = [
    {"model": "iPhone 17", "capacity": "256", "store": "A", "price": 120000},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "B", "price": 182000},
    {"model": "iPhone 17 Pro Max", "capacity": "256", "store": "C", "price": 198000},
    {"model": "iPhone 17 Air", "capacity": "256", "store": "D", "price": 150000},
    {"model": "iPhone 16", "capacity": "128", "store": "E", "price": 90000},
    {"model": "iPhone 16e", "capacity": "128", "store": "F", "price": 70000},
]


def test_bulk_quote_without_variant_uses_base_model():
    quote = ai.quote_bulk_request("17 256 x2", ROWS)
    assert quote["rows"] == [{"product": "iPhone 17 256", "store": "A", "unit_price": 120000, "quantity": 2, "subtotal": 240000}]
    assert quote["total"] == 240000


def test_bulk_quote_variants():
    quote = ai.quote_bulk_request("17 pro max 256 x1 と 17 air 256 x1 と 16e 128 x3 と 16 128 x1", ROWS)
    assert [(row["product"], row["unit_price"], row["quantity"]) for row in quote["rows"]] == [
        ("iPhone 17 Pro Max 256", 198000, 1),
        ("iPhone 17 Air 256", 150000, 1),
        ("iPhone 16e 128", 70000, 3),
        ("iPhone 16 128", 90000, 1),
    ]
    assert quote["total"] == 198000 + 150000 + 210000 + 90000


def test_16e_and_air_are_recognised_in_questions():
    assert [row["model"] for row in ai.filter_price_context_for_message("iPhone 16e 多少钱", ROWS)] == ["iPhone 16e"]
    assert [row["model"] for row in ai.filter_price_context_for_message("iPhone 17 Air の価格", ROWS)] == ["iPhone 17 Air"]
    # A general question without a variant still shows the whole generation.
    assert len(ai.filter_price_context_for_message("iPhone 17 256GB 价格", ROWS)) == 4
