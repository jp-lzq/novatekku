"""Colour prices in the AI evidence: "17 Pro 256 シルバー はいくら？"."""

from datetime import date

import pytest

from app.ai_gateway.evidence import build_price_evidence
from app.ai_gateway.evidence.colors import requested_quote, rows_for, summarise_colors
from app.ai_gateway.evidence.loaders import color_rows_from_assessment
from app.ai_gateway.evidence.render import LABELS, color_line
from app.ai_gateway.understanding import understand
from app.ai_gateway.verify import verify_answer
from app.ai_gateway.verify.facts import known_values, store_prices

NAMES = {
    "silver": ("シルバー", "银色", "Silver"),
    "deep-blue": ("ディープブルー", "深蓝色", "Deep Blue"),
    "cosmic-orange": ("コズミックオレンジ", "宇宙橙色", "Cosmic Orange"),
}


def color_row(code, store, price, exact=True, model="iPhone 17 Pro", capacity="256"):
    ja, zh, en = NAMES[code]
    return {"model": model, "capacity": capacity, "color_code": code, "color_name_ja": ja, "color_name_zh": zh,
            "color_name_en": en, "store": store, "price": price, "exact": exact}


COLOR_ROWS = [
    color_row("cosmic-orange", "森森買取", 210000),
    color_row("cosmic-orange", "アキモバ", 208000),
    color_row("deep-blue", "森森買取", 206000),
    color_row("silver", "アキモバ", 203000),
    color_row("silver", "森森買取", 201000),
    # a store paying one price for every colour appears once per colour, not exact
    color_row("cosmic-orange", "携帯空間", 204000, exact=False),
    color_row("deep-blue", "携帯空間", 204000, exact=False),
    color_row("silver", "携帯空間", 204000, exact=False),
    color_row("silver", "森森買取", 230000, capacity="512"),
]


def test_colour_ranking_and_shared_quote():
    summary = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256")
    assert [(color["code"], color["best_price"], color["best_store"]) for color in summary["colors"]] == [
        ("cosmic-orange", 210000, "森森買取"), ("deep-blue", 206000, "森森買取"), ("silver", 203000, "アキモバ")]
    assert [color["behind_top"] for color in summary["colors"]] == [0, 4000, 7000]
    assert summary["colors"][0]["store_count"] == 2 and summary["colors"][0]["rank"] == 1
    assert summary["all_colors"] == {"best_price": 204000, "best_store": "携帯空間", "store_count": 1}
    assert summary["top_color"] == "cosmic-orange" and summary["color_spread"] == 7000
    assert summary["requested"] is None


def test_requested_colour_takes_the_better_of_its_own_and_the_shared_price():
    silver = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256", "silver")["requested"]
    assert silver["best_price"] == 204000 and silver["best_store"] == "携帯空間" and silver["source"] == "all_colors"
    assert silver["rank"] == 3 and silver["behind_top"] == 6000 and silver["top_color"] == "cosmic-orange"
    assert silver["names"]["ja"] == "シルバー" and silver["quoted"] is True
    orange = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256", "cosmic-orange")["requested"]
    assert orange["best_price"] == 210000 and orange["source"] == "color" and orange["behind_top"] == 0 and orange["rank"] == 1


def test_requested_colour_without_its_own_quote():
    rows = [row for row in COLOR_ROWS if row["color_code"] != "deep-blue" or not row["exact"]]
    blue = summarise_colors(rows, "iPhone 17 Pro", "256", "deep-blue")["requested"]
    assert blue["source"] == "all_colors" and blue["rank"] is None and blue["best_price"] == 204000
    exact_only = [row for row in rows if row["exact"]]
    unquoted = summarise_colors(exact_only, "iPhone 17 Pro", "256", "deep-blue")["requested"]
    assert unquoted["quoted"] is False and "best_price" not in unquoted and unquoted["names"]["ja"] == "deep-blue"


def test_tie_between_own_and_shared_prefers_the_colour_quote():
    rows = [color_row("silver", "A店", 204000), color_row("silver", "B店", 204000, exact=False)]
    assert summarise_colors(rows, "iPhone 17 Pro", "256", "silver")["requested"]["source"] == "color"


def test_only_shared_quotes():
    rows = [row for row in COLOR_ROWS if not row["exact"]]
    summary = summarise_colors(rows, "iPhone 17 Pro", "256", "silver")
    assert summary["colors"] == [] and summary["top_color"] is None and summary["color_spread"] == 0
    assert summary["requested"]["best_price"] == 204000 and summary["requested"]["behind_top"] == 0


def test_no_colour_rows():
    assert summarise_colors(COLOR_ROWS, "iPhone 16e", "128") is None
    assert summarise_colors([], "iPhone 17 Pro", "256", "silver") is None
    assert len(rows_for(COLOR_ROWS, "iPhone 17 Pro", "512")) == 1
    assert len(rows_for(COLOR_ROWS, "iPhone 17 Pro", "256GB")) == 0  # capacity is normalised by the caller


def test_rows_skip_bad_quotes():
    rows = COLOR_ROWS + [color_row("silver", "", 999999), color_row("silver", "ゼロ店", 0), {**color_row("silver", "X", 1), "color_code": None}]
    assert summarise_colors(rows, "iPhone 17 Pro", "256")["colors"][2]["best_price"] == 203000


def test_requested_quote_helper_without_names():
    summary = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256")
    assert requested_quote(summary, "gold", None) == {"code": "gold", "names": {"ja": "gold", "zh": "gold", "en": "gold"},
                                                      "quoted": True, "best_price": 204000, "best_store": "携帯空間",
                                                      "source": "all_colors", "rank": None, "color_count": 3,
                                                      "top_color": "cosmic-orange",
                                                      "top_color_names": {"ja": "コズミックオレンジ", "zh": "宇宙橙色", "en": "Cosmic Orange"},
                                                      "behind_top": 6000}


def test_rows_from_the_assessment_working_set():
    data = {
        "products": [{"id": 1, "model": "iPhone 17 Pro", "capacity": "256GB", "colors": [
            {"variant_id": 11, "code": "silver", "name_ja": "シルバー", "name_en": "Silver", "name_zh": "银色"}]}],
        "stores": [{"id": 5, "name": "森森買取"}, {"id": 6, "name": "外れ店"}],
        "offers": [
            {"store_id": 5, "product_id": 1, "variant_id": 11, "price": 201000, "exact": True},
            {"store_id": 6, "product_id": 1, "variant_id": 11, "price": 260000, "exact": True},  # not accepted
            {"store_id": 5, "product_id": 1, "variant_id": 99, "price": 1, "exact": True},  # unknown variant
        ],
    }
    rows = color_rows_from_assessment(data, {(1, 5)})
    assert rows == [{"model": "iPhone 17 Pro", "capacity": "256", "color_code": "silver", "color_name_ja": "シルバー",
                     "color_name_en": "Silver", "color_name_zh": "银色", "store": "森森買取", "price": 201000, "exact": True}]
    assert color_rows_from_assessment({}, set()) == []


@pytest.mark.parametrize("language, expected", [
    ("ja", "シルバー: 最高 ¥204,000 (携帯空間) [全色同額の店] / 最高色のコズミックオレンジより -¥6,000"),
    ("zh", "银色：最高 ¥204,000（携帯空間） [所有颜色同价的店] / 比最高的宇宙橙色低 -¥6,000"),
    ("en", "Silver: best ¥204,000 (携帯空間) [a store paying the same for every colour] / -¥6,000 vs the top colour Cosmic Orange"),
])
def test_colour_line(language, expected):
    summary = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256", "silver")
    assert color_line(summary, LABELS[language], language) == expected


def test_colour_line_top_range_and_unquoted():
    top = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256", "cosmic-orange")
    assert color_line(top, LABELS["ja"], "ja") == "コズミックオレンジ: 最高 ¥210,000 (森森買取) / 3色中1位"
    plain = summarise_colors(COLOR_ROWS, "iPhone 17 Pro", "256")
    assert color_line(plain, LABELS["ja"], "ja") == "色別: コズミックオレンジ ¥210,000, ディープブルー ¥206,000, シルバー ¥203,000"
    exact_only = [row for row in COLOR_ROWS if row["exact"] and row["color_code"] != "deep-blue"]
    assert color_line(summarise_colors(exact_only, "iPhone 17 Pro", "256", "deep-blue"), LABELS["ja"], "ja") == \
        "deep-blue: この色の価格はありません"
    single = summarise_colors([color_row("silver", "A店", 200000)], "iPhone 17 Pro", "256")
    assert color_line(single, LABELS["ja"], "ja") is None  # one colour: nothing to compare


ROWS = [
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "森森買取", "price": 210000, "retail_price": 219800},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "アキモバ", "price": 208000, "retail_price": 219800},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "携帯空間", "price": 204000, "retail_price": 219800},
    {"model": "iPhone 17 Pro", "capacity": "512", "store": "森森買取", "price": 230000, "retail_price": 254800},
]


def evidence(message, rows=COLOR_ROWS):
    return build_price_evidence(understand(message).to_dict(), ROWS, color_rows=rows, today=date(2026, 11, 24))


def test_evidence_carries_the_asked_colour():
    result = evidence("iPhone 17 Pro 256 シルバー いくら")
    colors = result["items"][0]["capacities"][0]["colors"]
    assert colors["requested"]["code"] == "silver" and colors["requested"]["best_price"] == 204000
    assert any(line.startswith("シルバー: 最高 ¥204,000") for line in result["lines"]["ja"])
    assert any(line.startswith("Silver: best ¥204,000") for line in result["lines"]["en"])


def test_colour_lines_only_for_a_single_capacity():
    result = evidence("17 pro シルバー いくら")
    assert len(result["items"][0]["capacities"]) == 2
    assert not any("シルバー:" in line for line in result["lines"]["ja"])


def test_evidence_without_colour_rows():
    result = evidence("iPhone 17 Pro 256 シルバー いくら", rows=[])
    assert result["items"][0]["capacities"][0]["colors"] is None
    assert not any("シルバー" in line for line in result["lines"]["ja"])


def test_colour_amounts_and_store_prices_are_known():
    result = evidence("iPhone 17 Pro 256 シルバー いくら")
    values = known_values(result)
    assert ("JPY", 203000) in values and ("JPY", 6000) in values and ("JPY", 7000) in values
    prices = store_prices(result)
    assert 203000 in prices["アキモバ"] and 206000 in prices["森森買取"]


def test_colour_price_of_a_store_is_not_flagged():
    result = evidence("iPhone 17 Pro 256 シルバー いくら")
    answer = "シルバーならアキモバが 203,000円、携帯空間なら全色同じ 204,000円です。最高色より 6,000円安くなります。"
    report = verify_answer(answer, result, ROWS)
    assert report.status == "ok", report.findings
    wrong = verify_answer("シルバーならアキモバが 199,000円です。", result, ROWS)
    assert wrong.status == "warning"


def test_load_color_rows_uses_the_colour_page_data_and_caches_it(monkeypatch):
    from app.ai_gateway.evidence import loaders
    from app.web.routers import prices

    calls = []
    data = {"products": [{"id": 1, "model": "iPhone 17 Pro", "capacity": "256", "colors": [
                {"variant_id": 11, "code": "silver", "name_ja": "シルバー", "name_en": "Silver", "name_zh": "银色"}]},
                         {"id": 2, "model": "iPhone 16e", "capacity": "128", "colors": [
                {"variant_id": 21, "code": "white", "name_ja": "ホワイト", "name_en": "White", "name_zh": "白色"}]}],
            "stores": [{"id": 5, "name": "森森買取"}],
            "offers": [{"store_id": 5, "product_id": 1, "variant_id": 11, "price": 201000, "exact": True},
                       {"store_id": 5, "product_id": 2, "variant_id": 21, "price": 80000, "exact": False}]}
    monkeypatch.setattr(prices, "_assessment_data", lambda db: calls.append("data") or data)
    monkeypatch.setattr(prices, "_accepted_price_keys", lambda db, ids: {(1, 5, 201000), (2, 5, 80000)})
    loaders.COLOR_ROWS_CACHE.clear()
    try:
        rows = loaders.load_color_rows(object(), {"iPhone 17 Pro"})
        assert [(row["model"], row["color_code"], row["price"]) for row in rows] == [("iPhone 17 Pro", "silver", 201000)]
        assert [row["model"] for row in loaders.load_color_rows(object(), {"iPhone 16e"})] == ["iPhone 16e"]
        assert calls == ["data"]  # the second question used the cached working set
        assert loaders.load_color_rows(object(), set()) == []
    finally:
        loaders.COLOR_ROWS_CACHE.clear()
