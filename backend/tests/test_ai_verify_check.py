"""Checking answer amounts and store prices against the evidence."""

from datetime import date, timedelta

from app.ai_gateway.evidence import build_price_evidence
from app.ai_gateway.understanding import understand
from app.ai_gateway.verify import verify_answer
from app.ai_gateway.verify.facts import known_values, store_prices

TODAY = date(2026, 11, 12)
ROWS = [
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "携帯空間", "price": 175500, "retail_price": 194800,
     "market_average": 171900},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "買取ソムリエ", "price": 175500, "retail_price": 194800},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "アキモバ", "price": 172000, "retail_price": 194800},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "森森買取", "price": 168000, "retail_price": 194800},
    {"model": "iPhone 16e", "capacity": "128", "store": "アキモバ", "price": 82000},
]
MARKETS = [{"market": "hk", "model": "iPhone 17 Pro", "capacity": "256", "color_code": "silver", "price": 9000,
            "currency": "HKD", "offers": 1}]
DAILY = {("iPhone 17 Pro", "256"): [(TODAY - timedelta(days=7), 177500), (TODAY, 175500)]}


def evidence(message):
    return build_price_evidence(understand(message).to_dict(), ROWS, daily_best=DAILY, market_rows=MARKETS,
                                fx_rates={"HKD": {"rate": 20.0}}, today=TODAY)


EV = evidence("17 pro 256 いくら")


def test_real_answer_from_the_site_is_confirmed():
    answer = ("iPhone 17 Pro 256GBの買取市場平均は171,900円、中央値は172,000円です。"
              "最高額は携帯空間と買取ソムリエの175,500円です。")
    report = verify_answer(answer, EV, ROWS)
    assert report.status == "ok"
    assert (report.checked, report.supported) == (3, 3)


def test_invented_amount_is_reported():
    report = verify_answer("最高は 181,000円 です。", EV, ROWS)
    assert report.status == "warning"
    assert [(f.kind, f.value) for f in report.findings] == [("unsupported_amount", 181000)]


def test_right_number_at_the_wrong_store():
    report = verify_answer("森森買取なら175,500円で売れます。", EV, ROWS)
    kinds = [(f.kind, f.store) for f in report.findings]
    assert ("wrong_store_price", "森森買取") in kinds
    assert next(f for f in report.findings if f.kind == "wrong_store_price").expected == [168000]


def test_sentence_with_several_stores_is_not_paired():
    report = verify_answer("携帯空間と森森買取は175,500円です。", EV, ROWS)
    assert all(f.kind != "wrong_store_price" for f in report.findings)


def test_rounded_and_approximate_amounts():
    assert verify_answer("最高は約17.6万円です。", EV, ROWS).status == "ok"  # 175,500 rounds to 17.6万
    assert verify_answer("最高は17.5万円です。", EV, ROWS).status == "ok"  # within the 1,000-yen rounding shown
    assert verify_answer("最高は約176,000円です。", EV, ROWS).status == "ok"  # approximate: within 1 %
    assert verify_answer("最高は176,000円です。", EV, ROWS).status == "warning"  # exact figure that is not a fact


def test_differences_trend_overseas_and_retail():
    answer = ("定価194,800円より19,300円安く、1週間前より2,000円下がりました。"
              "香港ではHK$9,000（約180,000円）です。")
    report = verify_answer(answer, EV, ROWS)
    assert report.status == "ok", report.findings


def test_bulk_totals_are_known():
    ev = evidence("17 pro 256 x2 と 16e 128 x3 合計")
    assert verify_answer("合計は597,000円です。", ev, ROWS).status == "ok"


def test_no_evidence_is_never_ok():
    assert verify_answer("最高は175,500円です。", {}, ROWS).status == "no_evidence"
    assert verify_answer("最高は175,500円です。", evidence("ビットコインの価格"), ROWS).status == "no_evidence"


def test_answer_without_amounts():
    assert verify_answer("今は売り時です。", EV, ROWS).status == "no_amounts"


def test_fact_index_and_store_prices():
    values = known_values(EV)
    assert any("best price" in label for label in values[("JPY", 175500)])
    assert ("HKD", 9000) in values and ("JPY", 180000) in values
    assert store_prices(EV, ROWS)["森森買取"] == {168000}
    assert "アキモバ" in store_prices(EV, ROWS) and 82000 not in store_prices(EV, ROWS)["アキモバ"]


def test_report_is_json_ready():
    import json

    json.dumps(verify_answer("森森買取なら175,500円", EV, ROWS).to_dict(), ensure_ascii=False)


def test_difference_between_two_phones_is_known():
    ev = evidence("17 pro 256 と 16e 128 どっちが高い？")
    assert verify_answer("17 Pro の方が 93,500円 高く売れます。", ev, ROWS).status == "ok"  # 175,500 - 82,000
    assert verify_answer("17 Pro の方が 90,000円 高く売れます。", ev, ROWS).status == "warning"
