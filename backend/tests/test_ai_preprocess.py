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
