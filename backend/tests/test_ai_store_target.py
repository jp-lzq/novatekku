"""Store-against-store and target-price evidence: matching, numbers, lines and the answer check."""

from datetime import date, timedelta

import pytest

from app.ai_gateway.evidence import build_price_evidence
from app.ai_gateway.evidence.render import LABELS, store_compare_lines, target_lines
from app.ai_gateway.evidence.store_compare import compare_stores, mentioned_stores, store_keys
from app.ai_gateway.evidence.target_price import assess_target
from app.ai_gateway.understanding import understand
from app.ai_gateway.verify import verify_answer
from app.ai_gateway.verify.facts import known_values, store_prices

TODAY = date(2026, 11, 12)
ROWS = [
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "携帯空間", "price": 175500},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "アキモバ", "price": 172000},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "アキモバ", "price": 170000},  # a second colour row
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "森森買取", "price": 168000},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "Geo Mobile", "price": 160000},
    {"model": "iPhone 17 Pro", "capacity": "512", "store": "携帯空間", "price": 203500},
    {"model": "iPhone 17 Pro", "capacity": "512", "store": "アキモバ", "price": 201000},
    {"model": "iPhone 17 Pro", "capacity": "1TB", "store": "ゲストモバイル", "price": 219200},
    {"model": "iPhone 16e", "capacity": "128", "store": "買取楽園", "price": 90000},
    {"model": "iPhone 16e", "capacity": "128", "store": "アキモバ", "price": 87000},
]
STORES = {row["store"] for row in ROWS}
DAILY = {("iPhone 17 Pro", "256"): [(TODAY - timedelta(days=7), 178000), (TODAY, 175500)]}


def evidence(message):
    return build_price_evidence(understand(message).to_dict(), ROWS, daily_best=DAILY, today=TODAY)


# --- finding the stores ---------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("森森買取とアキモバ どっち", ["森森買取", "アキモバ"]),
    ("アキモバと森森買取 どっち", ["アキモバ", "森森買取"]),  # in the order written
    ("あきもば と 携帯 空間", ["アキモバ", "携帯空間"]),  # hiragana and a space
    ("ｱｷﾓﾊﾞ", ["アキモバ"]),  # half-width katakana
    ("森森 は？", ["森森買取"]),  # without the generic "買取"
    ("geo mobile or GEOMOBILE", ["Geo Mobile"]),  # case and spaces
    ("ゲストモバイル", ["ゲストモバイル"]),
    ("どこが一番高い", []),
])
def test_mentioned_stores(text, expected):
    assert mentioned_stores(text, STORES) == expected


def test_a_longer_store_name_wins_over_the_shorter_one_inside_it():
    stores = {"森森買取", "森森買取 渋谷店"}
    assert mentioned_stores("森森買取渋谷店はいくら", stores) == ["森森買取 渋谷店"]
    assert mentioned_stores("森森買取はいくら", stores) == ["森森買取"]


def test_ascii_store_names_need_word_boundaries():
    assert mentioned_stores("geolocation", {"Geo Shop"}) == []
    assert mentioned_stores("geo は？", {"Geo Shop"}) == ["Geo Shop"]


def test_generic_cores_are_not_store_names():
    assert store_keys("iPhone買取") == ["iphone買取"]
    assert mentioned_stores("iphone 17 pro いくら", {"iPhone買取"}) == []
    assert store_keys("森森買取") == ["森森買取", "森森"]


# --- comparing them -------------------------------------------------------

def test_compare_two_stores():
    rows = [row for row in ROWS if row["model"] == "iPhone 17 Pro" and row["capacity"] == "256"]
    result = compare_stores(rows, ["森森買取", "アキモバ"])
    assert [(s["store"], s["price"], s["rank"], s["behind_best"]) for s in result["stores"]] == [
        ("アキモバ", 172000, 2, 3500), ("森森買取", 168000, 3, 7500)]
    assert result["winner"] == "アキモバ" and result["gap"] == 4000 and result["tie"] is False
    assert result["best_store"] == "携帯空間" and result["best_price"] == 175500 and result["store_count"] == 4
    assert result["best_is_asked"] is False and result["gap_to_best"] == 3500
    assert result["unquoted"] == []


def test_compare_with_the_best_store_and_an_unquoted_one():
    rows = [row for row in ROWS if row["model"] == "iPhone 17 Pro" and row["capacity"] == "256"]
    result = compare_stores(rows, ["携帯空間", "ゲストモバイル"])
    assert result["winner"] is None and result["gap"] is None  # only one asked store has a quote
    assert result["best_is_asked"] is True and result["gap_to_best"] is None
    assert result["unquoted"] == ["ゲストモバイル"]


def test_compare_tie():
    rows = [{"store": "A店舗", "price": 100000}, {"store": "B店舗", "price": 100000}]
    result = compare_stores(rows, ["A店舗", "B店舗"])
    assert result["tie"] is True and result["winner"] is None and result["gap"] == 0


def test_store_comparison_in_the_evidence():
    result = evidence("森森買取とアキモバ、17 Pro 256 はどっちが高い？")
    assert result["store_compare"]["stores"] == ["森森買取", "アキモバ"]
    [item] = result["store_compare"]["items"]
    assert (item["model"], item["capacity"], item["winner"], item["gap"]) == ("iPhone 17 Pro", "256", "アキモバ", 4000)
    assert result["target_price"] is None


def test_store_comparison_for_every_quoted_capacity_without_a_capacity():
    result = evidence("携帯空間とアキモバ、17 pro はどっちが高い？")
    assert [item["capacity"] for item in result["store_compare"]["items"]] == ["256", "512", "1TB"]
    one_tb = result["store_compare"]["items"][2]
    assert one_tb["stores"] == [] and one_tb["unquoted"] == ["携帯空間", "アキモバ"]


def test_no_store_named_no_comparison():
    assert evidence("17 pro 256 いくら")["store_compare"] is None


def test_store_comparison_lines():
    result = evidence("森森買取とアキモバ、17 Pro 256 はどっちが高い？")
    ja = result["lines"]["ja"][-1]
    assert ja == ("iPhone 17 Pro 256GB 店舗比較: アキモバ ¥172,000 (2位/4店) / 森森買取 ¥168,000 (3位)"
                  " → アキモバが 森森買取より ¥4,000 高い / 最高は 携帯空間 ¥175,500（¥3,500 高い）")
    assert "アキモバ比森森買取高 ¥4,000" in result["lines"]["zh"][-1]
    assert "アキモバ pays ¥4,000 more than 森森買取" in result["lines"]["en"][-1]


def test_store_comparison_lines_tie_and_unquoted():
    comparison = {"items": [{"model": "iPhone 16e", "capacity": "128", "store_count": 2, "tie": True, "winner": None,
                             "stores": [{"store": "A", "price": 90000, "rank": 1}, {"store": "B", "price": 90000, "rank": 1}],
                             "unquoted": ["C"], "gap_to_best": None}]}
    lines = store_compare_lines(comparison, LABELS["en"])
    assert lines[0].endswith("→ same price")
    assert lines[1] == "C: no price for this model and capacity"


# --- the target price -----------------------------------------------------

RANKING = [{"store": "携帯空間", "price": 203500}, {"store": "アキモバ", "price": 201000}, {"store": "森森買取", "price": 180000}]


def test_target_reached():
    result = assess_target(RANKING, 200000, {"direction": "up", "change_7d": {"change": 1500}})
    assert result["reached"] is True and result["reached_count"] == 2
    assert result["stores"] == [{"store": "携帯空間", "price": 203500, "over_target": 3500},
                                {"store": "アキモバ", "price": 201000, "over_target": 1000}]
    assert result["best_vs_target"] == 3500 and result["shortfall"] == 0
    assert result["direction"] == "up" and result["change_7d"] == 1500


def test_target_missed():
    result = assess_target(RANKING, 210000)
    assert result["reached"] is False and result["reached_count"] == 0 and result["stores"] == []
    assert result["best_price"] == 203500 and result["best_store"] == "携帯空間"
    assert result["best_vs_target"] == -6500 and result["shortfall"] == 6500
    assert result["direction"] is None


def test_target_exactly_met_and_at_most_five_stores():
    ranking = [{"store": f"店{i}", "price": 200000} for i in range(7)]
    result = assess_target(ranking, 200000)
    assert result["reached_count"] == 7 and len(result["stores"]) == 5
    assert result["stores"][0]["over_target"] == 0


def test_target_in_the_evidence():
    result = evidence("17 Pro 256 は17万円以上で売れる？")
    [item] = result["target_price"]["items"]
    assert result["target_price"]["target"] == 170000
    assert [store["store"] for store in item["stores"]] == ["携帯空間", "アキモバ"]
    assert item["direction"] == "down" and item["change_7d"] == -2500
    assert result["lines"]["ja"][-1] == ("iPhone 17 Pro 256GB 目標 ¥170,000: 達成 2店: 携帯空間 ¥175,500, アキモバ ¥172,000"
                                         " / 最高 ¥175,500（携帯空間）目標比 +¥5,500 / 7日前比 -¥2,500 下落")


def test_target_without_capacity_answers_each_capacity():
    result = evidence("17 pro 能卖到18万吗")
    items = result["target_price"]["items"]
    assert [(item["capacity"], item["reached"]) for item in items] == [("256", False), ("512", True), ("1TB", True)]
    assert "还差 ¥4,500" in result["lines"]["zh"][-3]


def test_an_amount_that_is_not_a_target_builds_nothing():
    assert evidence("17 pro 256 と 16e 128 の差は8万円くらい？")["target_price"] is None


def test_target_lines_mention_more_stores():
    assessment = {"items": [{"model": "iPhone 16e", "capacity": "128", "target": 80000, "reached": True, "reached_count": 7,
                             "stores": [{"store": f"S{i}", "price": 90000} for i in range(5)], "best_price": 90000,
                             "best_store": "S0", "best_vs_target": 10000, "change_7d": None, "direction": None}]}
    [line] = target_lines(assessment, LABELS["en"])
    assert "7 store(s) reach it" in line and "2 more" in line and "vs 7 days ago" not in line


# --- the answer check -----------------------------------------------------

def test_store_comparison_numbers_are_known_facts():
    result = evidence("森森買取とアキモバ、17 Pro 256 はどっちが高い？")
    values = known_values(result)
    assert ("JPY", 4000) in values  # アキモバ vs 森森買取
    assert ("JPY", 7500) in values  # 森森買取 behind the best store
    prices = store_prices(result)
    assert 7500 in prices["森森買取"] and 168000 in prices["森森買取"]


def test_a_store_below_the_top_five_is_still_a_valid_store_price():
    rows = [{"model": "iPhone 16e", "capacity": "128", "store": f"店舗{i}", "price": 90000 - i * 1000} for i in range(8)]
    result = build_price_evidence(understand("店舗7 と 店舗0、16e 128 はどっちが高い？").to_dict(), rows)
    assert 83000 in store_prices(result)["店舗7"]
    assert verify_answer("店舗7は 83,000円です。", result).status == "ok"


def test_store_comparison_answer_checks_out():
    result = evidence("森森買取とアキモバ、17 Pro 256 はどっちが高い？")
    answer = "アキモバは 172,000円、森森買取は 168,000円。アキモバが森森買取より 4,000円高いです。森森買取は最高値より 7,500円安い。"
    report = verify_answer(answer, result)
    assert report.status == "ok", report.to_dict()


def test_target_answer_checks_out_and_a_wrong_gap_does_not():
    result = evidence("17 Pro 256 は18万円以上で売れる？")
    assert verify_answer("最高は 175,500円で、18万円まであと 4,500円足りません。", result).status == "ok"
    assert verify_answer("18万円まであと 5,000円足りません。", result).status == "warning"


def test_target_store_gap_written_next_to_the_store():
    result = evidence("17 Pro 256 は17万円以上で売れる？")
    assert verify_answer("携帯空間なら目標より 5,500円多く売れます。", result).status == "ok"
