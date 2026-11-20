"""Global comparison: every market ranked in yen with a recommendation of where to sell."""

from datetime import date, timedelta

import pytest

from app.ai_gateway.evidence import build_price_evidence
from app.ai_gateway.evidence.global_compare import SMALL_GAP_PERCENT, advice_for, global_comparison
from app.ai_gateway.evidence.render import LABELS, advice_text, render_evidence
from app.ai_gateway.understanding import understand
from app.ai_gateway.verify.facts import known_values

QUOTES = {"best_price": 200000, "best_store": "森森買取", "store_count": 12}


def market(name, price_jpy, store=None, currency="USD", price=1000):
    entry = {"market": name, "price": price, "currency": currency, "price_jpy": price_jpy, "buyers": 3}
    if store:
        entry["best_store"] = store
    return entry


@pytest.mark.parametrize("gap, percent, expected", [
    (None, None, "japan_only"),
    (0, 0.0, "japan_best"),
    (-5000, -2.5, "japan_best"),
    (4000, 2.0, "overseas_small"),
    (9999, SMALL_GAP_PERCENT - 0.1, "overseas_small"),
    (10000, SMALL_GAP_PERCENT, "overseas_clear"),
    (30000, 15.0, "overseas_clear"),
])
def test_advice_thresholds(gap, percent, expected):
    assert advice_for(gap, percent) == expected


def test_japan_best():
    result = global_comparison(QUOTES, [market("hk", 190000, currency="HKD"), market("us", 150000, "Buyer A")])
    assert [(entry["rank"], entry["market"]) for entry in result["ranking"]] == [(1, "jp"), (2, "hk"), (3, "us")]
    assert result["advice"] == "japan_best" and result["best_market"] == "jp" and result["japan_rank"] == 1
    assert result["overseas_gap"] == -10000 and result["overseas_gap_percent"] == -5.0
    assert result["best_overseas_market"] == "hk" and result["spread"] == 50000
    assert [entry["behind_top"] for entry in result["ranking"]] == [0, 10000, 50000]
    assert result["ranking"][0]["store"] == "森森買取" and result["ranking"][2]["store"] == "Buyer A"


def test_small_overseas_lead_still_recommends_japan():
    result = global_comparison(QUOTES, [market("us", 206000, "Buyer A")])
    assert result["advice"] == "overseas_small" and result["overseas_gap"] == 6000 and result["overseas_gap_percent"] == 3.0
    assert result["best_market"] == "us" and result["japan_rank"] == 2 and result["best_overseas_store"] == "Buyer A"


def test_clear_overseas_lead():
    result = global_comparison(QUOTES, [market("hk", 230000, currency="HKD"), market("us", 210000)])
    assert result["advice"] == "overseas_clear" and result["best_overseas_market"] == "hk"
    assert result["overseas_gap"] == 30000 and result["overseas_gap_percent"] == 15.0


def test_tie_puts_japan_first():
    result = global_comparison(QUOTES, [market("us", 200000)])
    assert [entry["market"] for entry in result["ranking"]] == ["jp", "us"]
    assert result["advice"] == "japan_best"


def test_market_without_a_rate_is_left_out():
    result = global_comparison(QUOTES, [market("us", None)])
    assert [entry["market"] for entry in result["ranking"]] == ["jp"]
    assert result["advice"] == "japan_only" and result["overseas_gap"] is None and result["spread"] == 0


def test_without_a_japanese_price():
    assert global_comparison({}, [market("us", 150000)]) is None
    assert global_comparison({"best_price": 0}, [market("us", 150000)]) is None


@pytest.mark.parametrize("direction, expected", [("down", "down"), ("up", "up"), ("flat", "flat"), ("unknown", None), (None, None)])
def test_japan_direction(direction, expected):
    trend = {"direction": direction} if direction else None
    assert global_comparison(QUOTES, [market("us", 150000)], trend)["japan_direction"] == expected


def test_advice_text_in_every_language():
    small = global_comparison(QUOTES, [market("us", 206000)], {"direction": "down"})
    assert advice_text(small, LABELS["ja"]) == ("アメリカが ¥6,000 (+3.0%) 高いが、送料・手数料・為替で消える差なので日本で売るのが現実的"
                                               " / 日本の価格は下落中なので早めの売却がおすすめ")
    assert advice_text(small, LABELS["zh"]).startswith("美国高 ¥6,000 (+3.0%)")
    assert advice_text(small, LABELS["en"]).startswith("United States pays ¥6,000 (+3.0%) more")
    clear = global_comparison(QUOTES, [market("hk", 230000, currency="HKD")], {"direction": "down"})
    assert "下落中" not in advice_text(clear, LABELS["ja"])  # waiting is not the point when abroad pays clearly more
    rising = global_comparison(QUOTES, [market("hk", 150000, currency="HKD")], {"direction": "up"})
    assert advice_text(rising, LABELS["ja"]) == "日本が一番高いので日本で売るのがおすすめ / 日本の価格は上昇中"


ROWS = [
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "森森買取", "price": 200000, "retail_price": 219800},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "アキモバ", "price": 198000, "retail_price": 219800},
]
MARKETS = [
    {"market": "hk", "model": "iPhone 17 Pro", "capacity": "256", "color_code": "silver", "price": 10500, "currency": "HKD", "offers": 1},
    {"market": "us", "model": "iPhone 17 Pro", "capacity": "256", "color_code": None, "price": 1400, "currency": "USD", "offers": 5},
]
STORES = [{"market": "us", "store": "Buyer A", "model": "iPhone 17 Pro", "capacity": "256", "color_code": None,
           "price": 1400, "currency": "USD"}]
RATES = {"USD": {"rate": 150.0}, "HKD": {"rate": 20.0}}
TODAY = date(2026, 11, 20)


def evidence(message, **kwargs):
    return build_price_evidence(understand(message).to_dict(), ROWS, market_rows=MARKETS, market_store_rows=STORES,
                                fx_rates=RATES, today=TODAY, **kwargs)


def test_evidence_has_the_global_comparison():
    result = evidence("17 pro 256 世界で一番高く売れるのはどこ？",
                      daily_best={("iPhone 17 Pro", "256"): [(TODAY - timedelta(days=7), 205000), (TODAY, 200000)]})
    comparison = result["items"][0]["capacities"][0]["global"]
    assert [entry["price_jpy"] for entry in comparison["ranking"]] == [210000, 210000, 200000]
    assert {entry["market"] for entry in comparison["ranking"][:2]} == {"hk", "us"} and comparison["ranking"][2]["market"] == "jp"
    assert comparison["advice"] == "overseas_clear" and comparison["overseas_gap"] == 10000
    assert comparison["japan_direction"] == "down"


def test_global_line_only_for_overseas_questions():
    overseas = evidence("17 pro 256 世界で一番高く売れるのはどこ？")
    line = [text for text in overseas["lines"]["ja"] if "世界比較" in text]
    assert len(line) == 1
    assert "日本 ¥200,000 (森森買取)" in line[0] and "(Buyer A)" in line[0] and "→" in line[0]
    assert any("global comparison" in text for text in overseas["lines"]["en"])
    assert any("全球比较" in text for text in overseas["lines"]["zh"])
    plain = evidence("17 pro 256 いくら？")
    assert plain["items"][0]["capacities"][0]["global"] is not None
    assert not any("世界比較" in text for text in plain["lines"]["ja"])


def test_no_overseas_prices_means_no_comparison():
    result = build_price_evidence(understand("17 pro 256 海外ならいくら？").to_dict(), ROWS, fx_rates=RATES, today=TODAY)
    assert result["items"][0]["capacities"][0]["global"] is None
    assert not any("世界比較" in text for text in render_evidence(result, "ja"))


def test_comparison_amounts_are_known_facts():
    values = known_values(evidence("17 pro 256 世界で一番高く売れるのはどこ？"))
    assert any("best overseas vs Japan" in label for label in values[("JPY", 10000)])
    assert any("global spread" in label for label in values[("JPY", 10000)])
