"""Question understanding: spelling normalisation, device recognition, intents."""

import pytest

from app.ai_gateway.understanding import understand
from app.ai_gateway.understanding import intents as I
from app.ai_gateway.understanding.entities import capacity_without_model, extract_devices
from app.ai_gateway.understanding.normalize import compact, kanji_to_int, normalize_query


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("token,value", [
    ("七", 7), ("十", 10), ("十六", 16), ("十七", 17), ("二十", 20), ("二十一", 21), ("两", 2), ("", None), ("百", None),
])
def test_kanji_numbers(token, value):
    assert kanji_to_int(token) == value


@pytest.mark.parametrize("raw,expected", [
    ("ｉＰｈｏｎｅ１７　Ｐｒｏ", "iphone17 pro"),
    ("アイフォン17プロ", "iphone17プロ"),
    ("苹果手机十七pro", "iphone 17pro"),
    ("十六pm 1t", "16pm 1tb"),
    ("256G 白", "256gb 白"),
    ("1テラ", "1tb"),
    ("512ギガ", "512gb"),
    ("17 pro 256 ×3", "17 pro 256 x3"),
    ("いくら？！", "いくら"),
])
def test_normalize_query(raw, expected):
    assert normalize_query(raw) == expected


@pytest.mark.parametrize("raw", ["5G対応", "5g network", "4g回線"])
def test_network_generations_are_not_storage(raw):
    assert "gb" not in normalize_query(raw)


def test_ordinary_kanji_words_are_kept():
    assert normalize_query("一番高い店") == "一番高い店"
    assert normalize_query("一緒に売る") == "一緒に売る"


def test_compact_removes_separators():
    assert compact("iPhone 17 Pro-Max / 256 GB") == "iphone17promax256gb"


# ---------------------------------------------------------------------------
# devices
# ---------------------------------------------------------------------------

def one(message):
    devices = extract_devices(message)
    assert len(devices) == 1, devices
    return devices[0]


@pytest.mark.parametrize("message,model", [
    ("iPhone 17 Pro Max 256GB", "iPhone 17 Pro Max"),
    ("17promax", "iPhone 17 Pro Max"),
    ("17pm 256", "iPhone 17 Pro Max"),
    ("17プロマ 256", "iPhone 17 Pro Max"),
    ("17プロマックス", "iPhone 17 Pro Max"),
    ("iphone17 max", "iPhone 17 Pro Max"),
    ("十七pro 256", "iPhone 17 Pro"),
    ("iPhone17プロ", "iPhone 17 Pro"),
    ("16 plus 128", "iPhone 16 Plus"),
    ("15+ 128", "iPhone 15 Plus"),
    ("17 air 256", "iPhone 17 Air"),
    ("17エア 256", "iPhone 17 Air"),
    ("16e 128", "iPhone 16e"),
    ("iphone 17e", "iPhone 17e"),
    ("iphone 17 256", "iPhone 17"),
    ("18 pro max 1tb", "iPhone 18 Pro Max"),
    ("iPhone Duo 512", "iPhone Duo"),
    ("折りたたみiPhone 1TB", "iPhone Duo"),
    ("デュオ 2T", "iPhone Duo"),
])
def test_models(message, model):
    assert one(message).model == model


@pytest.mark.parametrize("message,capacity", [
    ("17 pro 256", "256"), ("17 pro 256gb", "256"), ("17 pro 256G", "256"), ("17 pro 1tb", "1TB"),
    ("17 pro 1T", "1TB"), ("17 pro max 2TB", "2TB"), ("17 pro 1024gb", "1TB"), ("16 128", "128"),
    ("17 pro 1テラ", "1TB"), ("17 pro", None), ("17 pro 300gb", None),
])
def test_capacities(message, capacity):
    assert one(message).capacity == capacity


@pytest.mark.parametrize("message,color", [
    ("17 pro 256 ディープブルー", "deep-blue"),
    ("17 pro 256 深蓝", "deep-blue"),
    ("17 pro max 512 cosmic orange", "cosmic-orange"),
    ("17 256 ラベンダー", "lavender"),
    ("iPhone Duo 256 ナイトスカイ", "night-sky"),
    ("iphone duo 256 star white", "star-white"),
    ("16 pro 256 デザート", "desert-titanium"),
    ("17 pro 256", None),
])
def test_colours_use_the_catalogue(message, color):
    assert one(message).color == color


@pytest.mark.parametrize("message,condition", [
    ("17 pro 256 未開封", "sealed"), ("17 pro 256 新品", "new"), ("17 pro 256 開封済み", "opened"),
    ("17 pro 256 中古 美品", "used"), ("17 pro 256 二手", "used"), ("17 pro 256 画面割れ", "broken"),
    ("17 pro 256 sealed", "sealed"), ("17 pro 256", None),
])
def test_conditions(message, condition):
    assert one(message).condition == condition


@pytest.mark.parametrize("message,carrier", [
    ("17 pro 256 SIMフリー", "sim_free"), ("17 pro 256 docomo", "docomo"), ("17 pro 256 ドコモ版", "docomo"),
    ("17 pro 256 ソフトバンク", "softbank"), ("17 pro 256 港版", "hk_model"), ("17 pro 256 unlocked", "sim_free"),
])
def test_carriers(message, carrier):
    assert one(message).carrier == carrier


@pytest.mark.parametrize("message,quantity", [
    ("17 pro 256 x3", 3), ("17 pro 256 ×2", 2), ("17 pro 256 *4", 4), ("17 pro 256 5台", 5),
    ("17 pro 256 2部", 2), ("17 pro 256 三台", 3), ("17 pro 256 10 units", 10), ("17 pro 256", 1),
])
def test_quantities(message, quantity):
    assert one(message).quantity == quantity


def test_attributes_belong_to_the_model_written_before_them():
    first, second = extract_devices("17 pro max 1tb 未開封 x2、16 pro 128 中古")
    assert (first.model, first.capacity, first.condition, first.quantity) == ("iPhone 17 Pro Max", "1TB", "sealed", 2)
    assert (second.model, second.capacity, second.condition, second.quantity) == ("iPhone 16 Pro", "128", "used", 1)


def test_two_capacities_of_the_same_model_stay_separate():
    devices = extract_devices("17 pro 256 と 17 pro 512 の差は？")
    assert [(d.model, d.capacity) for d in devices] == [("iPhone 17 Pro", "256"), ("iPhone 17 Pro", "512")]


def test_exact_repeat_is_merged():
    assert len(extract_devices("17 pro 256 ... やっぱり 17 pro")) == 1


def test_unknown_models_are_reported_not_dropped():
    device = one("iPhone 12 mini 64 売りたい")
    assert device.model == "iPhone 12 mini"
    assert device.known is False
    assert device.capacity == "64"


@pytest.mark.parametrize("message", [
    "12台あります",  # quantity, not iPhone 12
    "2024年に買った",  # a year
    "15時に行きます",  # a time
    "17万円で売れた",  # an amount of money
    "残り10回",
    "5G対応ですか",
])
def test_numbers_that_are_not_models(message):
    assert extract_devices(message) == []


def test_bare_generation_needs_phone_context():
    assert extract_devices("17 256") and extract_devices("16 売りたい")
    assert extract_devices("私は17歳") == []


def test_evidence_records_the_source_text():
    device = one("17プロマ 1t 未開封")
    assert device.evidence["model"] == "17プロマ"
    assert device.evidence["capacity"] == "1tb"
    assert device.evidence["condition"] == "未開封"


def test_follow_up_capacity():
    assert capacity_without_model("那 512 呢？") == "512"
    assert capacity_without_model("1TBは？") == "1TB"
    assert capacity_without_model("17 pro 512 は？") is None
    assert capacity_without_model("ありがとう") is None


# ---------------------------------------------------------------------------
# intents
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,intent", [
    ("iPhone 17 Pro 256GB はいくら？", I.PRICE_QUOTE),
    ("17 pro max 512 买取价格", I.PRICE_QUOTE),
    ("how much is iphone 17 pro 256", I.PRICE_QUOTE),
    ("17 pro 256", I.PRICE_QUOTE),
    ("那 512 呢？", I.PRICE_QUOTE),
    ("17 Pro Max 256 はどこが一番高い？", I.STORE_RANKING),
    ("哪家店收17pro最高价", I.STORE_RANKING),
    ("which store pays the most for iphone 16 pro", I.STORE_RANKING),
    ("17 pro と 16 pro max どっちが高く売れる？", I.MODEL_COMPARE),
    ("十六pm 1t 和 15 pro 哪个值钱", I.MODEL_COMPARE),
    ("compare iphone 17 air and iphone 17", I.MODEL_COMPARE),
    ("今は17 Proを売るタイミングですか？", I.SELL_TIMING),
    ("17 pro max 现在卖还是等等再卖", I.SELL_TIMING),
    ("should i sell my iphone 16 now or wait", I.SELL_TIMING),
    ("香港で売ったらいくら？ 17 pro max 512", I.OVERSEAS_MARKET),
    ("美国回收17pro多少钱", I.OVERSEAS_MARKET),
    ("iphone 17 price in hong kong", I.OVERSEAS_MARKET),
    ("16e 128 x3 と 17 256 x2 合計", I.BULK_QUOTE),
    ("17 pro 256 5台まとめて売りたい", I.BULK_QUOTE),
    ("iPhoneの種類は？", I.CATALOG),
    ("iphone有哪些型号", I.CATALOG),
    ("iPhone 17 Air の定価は？", I.RETAIL_PRICE),
    ("17 pro 官网价多少", I.RETAIL_PRICE),
    ("what is the apple price of iphone 17 air", I.RETAIL_PRICE),
    ("一番高い店の住所は？", I.STORE_INFO),
    ("这家店营业时间", I.STORE_INFO),
    ("AndroidからiPhoneへデータを移す方法は？", I.DEVICE_HELP),
    ("iphone 电池健康怎么看", I.DEVICE_HELP),
    ("how do i back up my iphone", I.DEVICE_HELP),
    ("こんにちは", I.GREETING),
    ("谢谢", I.GREETING),
    ("hello", I.GREETING),
    ("ビットコインの今の価格は？", I.OFF_TOPIC),
    ("今日の天気は？", I.OFF_TOPIC),
    ("what's the price of gold", I.OFF_TOPIC),
])
def test_intents(message, intent):
    assert understand(message).intent.intent == intent


def test_greeting_with_a_question_is_the_question():
    assert understand("こんにちは、17 pro 256 はいくら？").intent.intent == I.PRICE_QUOTE


def test_repeating_a_word_does_not_inflate_the_score():
    once = understand("いくら").intent.scores[I.PRICE_QUOTE]
    assert understand("いくら いくら いくら").intent.scores[I.PRICE_QUOTE] == once


def test_confidence_is_a_share_of_all_scores():
    clear = understand("iPhone 17 Pro 256GB はいくら？").intent
    mixed = understand("17 pro と 16 pro どっちを今売るべき？").intent
    assert clear.confidence == 1.0
    assert 0 < mixed.confidence < 1


def test_markets_are_listed():
    result = understand("香港とアメリカ、17 pro はどっちが高い？")
    assert result.intent.markets == ["hk", "us"]
    assert result.intent.intent == I.OVERSEAS_MARKET


def test_price_intents_need_the_price_table():
    assert understand("17 pro 256 いくら").intent.needs_prices is True
    assert understand("データ移行の方法").intent.needs_prices is False


# ---------------------------------------------------------------------------
# packaged result
# ---------------------------------------------------------------------------

def test_to_dict_is_json_ready_and_complete():
    import json

    data = understand("17プロマ 256 白 未開封 2台 どこが一番高い？").to_dict()
    json.dumps(data, ensure_ascii=False)
    assert data["version"] == "understanding-v1"
    assert data["intent"] == I.STORE_RANKING
    assert data["needs_prices"] is True
    device = data["devices"][0]
    assert device["model"] == "iPhone 17 Pro Max"
    assert device["capacity"] == "256"
    assert device["color"] == "silver"  # 白 is the Silver finish on the 17 Pro family
    assert device["condition"] == "sealed"
    assert device["quantity"] == 2
    assert "start" not in device


def test_unknown_models_are_listed():
    assert understand("iPhone 12 64 いくら").unknown_models == ["iPhone 12"]


@pytest.mark.parametrize("message", ["", "   ", "？？？", "a" * 5000, "17" * 300, "x" * 100 + "17 pro"])
def test_odd_input_never_raises(message):
    understand(message).to_dict()


# ---------------------------------------------------------------------------
# regressions found in review
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected", [
    ("16e×3 と 17×2 の合計", [("iPhone 16e", 3), ("iPhone 17", 2)]),
    ("17 pro max×2", [("iPhone 17 Pro Max", 2)]),
    ("17promax×2", [("iPhone 17 Pro Max", 2)]),
    ("16e 3台 17 2台", [("iPhone 16e", 3), ("iPhone 17", 2)]),
    ("两台17pro 三台16e", [("iPhone 17 Pro", 2), ("iPhone 16e", 3)]),
    ("我有两台17 pro", [("iPhone 17 Pro", 2)]),
    ("17 pro 用了3个月", [("iPhone 17 Pro", 1)]),
    ("iPhone Air 256 いくら", [("iPhone 17 Air", 1)]),
])
def test_quantities_and_unnumbered_models(message, expected):
    assert [(d.model, d.quantity) for d in extract_devices(message)] == expected


@pytest.mark.parametrize("message,models", [
    ("17pro 256 12.5万で売れる？", ["iPhone 17 Pro"]),
    ("15:00に買取できますか", []),
    ("11/15に16を売りたい", ["iPhone 16"]),
    ("open until 11 pm", []),
    ("12pm", []),
    ("16 pm 256", ["iPhone 16 Pro Max"]),
    ("iPad Pro 13 買取", []),
    ("MacBook Air 13 売りたい", []),
    ("A18 Pro chip", []),
    ("iOS 18 iPhone 16 いくら", ["iPhone 16"]),
    ("Galaxy Z Fold 買取", []),
    ("小米14 pro 回收", []),
    ("Apple Watch Series 11 売る", []),
    ("I have a 17 pro", ["iPhone 17 Pro"]),
    ("折りたたみiPhone 1TB", ["iPhone Duo"]),
])
def test_other_numbers_and_products_are_not_iphones(message, models):
    assert [d.model for d in extract_devices(message)] == models


def test_carrier_at_the_end_of_the_sentence():
    assert one("17 pro 256 au").carrier == "au"


@pytest.mark.parametrize("message,intent", [
    ("17promax和16promax差多少钱", I.MODEL_COMPARE),
    ("17 pro 256と17 pro 512の差", I.MODEL_COMPARE),
    ("18が出たら17の買取価格は下がる？", I.SELL_TIMING),
    ("should i sell my 16 now or wait for the price drop", I.SELL_TIMING),
    ("17 proの買取価格は今後下がりますか", I.SELL_TIMING),
    ("お店はどこにありますか", I.STORE_INFO),
    ("Where is your shop?", I.STORE_INFO),
    ("similar price", I.OFF_TOPIC),
])
def test_intent_regressions(message, intent):
    assert understand(message).intent.intent == intent


@pytest.mark.parametrize("message,expected", [
    ("I want to sell my iPhone 16.", [("iPhone 16", None, 1)]),
    ("iPhone 17/256GB/ブラック", [("iPhone 17", "256", 1)]),
    ("17/256 いくら", [("iPhone 17", "256", 1)]),
    ("iphone 15/16 price", [("iPhone 15", None, 1), ("iPhone 16", None, 1)]),
    ("4x 17 pro", [("iPhone 17 Pro", None, 4)]),
    ("4x iPhone 16e 128 and 2x iPhone 17 256", [("iPhone 16e", "128", 4), ("iPhone 17", "256", 2)]),
    ("3/17に売る 17 pro", [("iPhone 17 Pro", None, 1)]),
    ("17 pro 256 x 3", [("iPhone 17 Pro", "256", 3)]),
])
def test_punctuation_slashes_and_leading_counts(message, expected):
    assert [(d.model, d.capacity, d.quantity) for d in extract_devices(message)] == expected
