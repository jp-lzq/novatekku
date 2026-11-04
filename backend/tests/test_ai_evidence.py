"""Price evidence: quotes, trend, overseas comparison, bulk totals and the database loaders."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai_gateway.evidence import build_price_evidence, collect_price_evidence
from app.ai_gateway.evidence.bulk import bulk_total
from app.ai_gateway.evidence.loaders import PAST_DAYS_CACHE, daily_best_from_history, load_daily_best, load_market_snapshots
from app.ai_gateway.evidence.matching import index_rows, match_device, normalise_capacity
from app.ai_gateway.evidence.overseas import best_overseas, compare_markets, to_yen
from app.ai_gateway.evidence.quotes import summarise_quotes
from app.ai_gateway.evidence.trend import summarise_trend, weekly_slope
from app.ai_gateway.understanding import understand
from app.db.models import MarketPrice, PriceHistory, Product, Store
from app.db.session import Base

RATES = {"USD": {"rate": 150.0}, "HKD": {"rate": 20.0}}


def row(model, capacity, store, price, **extra):
    return {"model": model, "capacity": capacity, "store": store, "price": price, **extra}


PRICE_ROWS = [
    row("iPhone 17 Pro", "256", "森森買取", 208000, retail_price=219800, market_average=205000, market_confidence="high"),
    row("iPhone 17 Pro", "256", "アキモバ", 206000, retail_price=219800),
    row("iPhone 17 Pro", "256", "買取商店", 204000, retail_price=219800, is_sponsored=True),
    row("iPhone 17 Pro", "512", "森森買取", 243000, retail_price=254800),
    row("iPhone 17 Pro", "512", "アキモバ", 245000, retail_price=254800),
    row("iPhone 16e", "128", "アキモバ", 80000, retail_price=99800),
    row("iPhone 16e", "128", "森森買取", 82000, retail_price=99800),
    row("iPhone Duo", "1TB", "アキモバ", 491000, retail_price=469800),
]


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("256", "256"), ("256GB", "256"), ("256 gb", "256"), ("1TB", "1TB"), ("1024", "1TB"), ("2048", "2TB"),
    ("1T", "1TB"), (None, None), ("", None),
])
def test_normalise_capacity(value, expected):
    assert normalise_capacity(value) == expected


def test_index_skips_rows_without_model_capacity_or_price():
    index = index_rows(PRICE_ROWS + [row(None, "256", "x", 1), row("iPhone 17", None, "x", 1), row("iPhone 17", "256", "x", 0)])
    assert sorted(index) == ["iPhone 16e", "iPhone 17 Pro", "iPhone Duo"]
    assert sorted(index["iPhone 17 Pro"]) == ["256", "512"]


def test_match_with_capacity():
    match = match_device({"model": "iPhone 17 Pro", "capacity": "256", "known": True}, index_rows(PRICE_ROWS))
    assert (match.capacities, match.notes) == (["256"], [])


def test_match_without_capacity_lists_every_quoted_capacity_smallest_first():
    match = match_device({"model": "iPhone 17 Pro", "capacity": None, "known": True}, index_rows(PRICE_ROWS))
    assert match.capacities == ["256", "512"]
    assert match.notes == ["capacity_missing"]


def test_match_unquoted_capacity_falls_back_to_quoted_ones():
    match = match_device({"model": "iPhone 17 Pro", "capacity": "1TB", "known": True}, index_rows(PRICE_ROWS))
    assert match.capacities == ["256", "512"]
    assert match.notes == ["capacity_not_quoted"]


def test_match_unknown_and_unquoted_models():
    index = index_rows(PRICE_ROWS)
    assert match_device({"model": "iPhone 12", "known": False}, index).notes == ["unknown_model"]
    assert match_device({"model": "iPhone 17 Air", "known": True}, index).notes == ["no_prices"]


# ---------------------------------------------------------------------------
# quotes
# ---------------------------------------------------------------------------

def test_quote_summary():
    summary = summarise_quotes([r for r in PRICE_ROWS if r["model"] == "iPhone 17 Pro" and r["capacity"] == "256"])
    assert summary["best_price"] == 208000
    assert summary["best_store"] == "森森買取"
    assert summary["runner_up_price"] == 206000
    assert summary["lead_over_runner_up"] == 2000
    assert summary["lowest_price"] == 204000
    assert summary["median_price"] == 206000
    assert summary["spread"] == 4000
    assert summary["store_count"] == 3
    assert summary["retail_price"] == 219800
    assert summary["best_vs_retail"] == -11800
    assert summary["best_vs_retail_percent"] == -5.4
    assert summary["market_average"] == 205000
    assert summary["market_confidence"] == "high"
    assert [item["store"] for item in summary["ranking"]] == ["森森買取", "アキモバ", "買取商店"]
    assert summary["sponsored_stores"] == ["買取商店"]


def test_quote_keeps_each_stores_best_colour():
    rows = [row("iPhone 17", "256", "A", 120000), row("iPhone 17", "256", "A", 125000), row("iPhone 17", "256", "B", 121000)]
    summary = summarise_quotes(rows)
    assert summary["store_count"] == 2
    assert summary["ranking"] == [{"store": "A", "price": 125000}, {"store": "B", "price": 121000}]


def test_quote_ties_are_ordered_by_store_name():
    summary = summarise_quotes([row("iPhone 17", "256", "B", 1000), row("iPhone 17", "256", "A", 1000)])
    assert summary["best_store"] == "A"


def test_quote_without_retail_or_runner_up():
    summary = summarise_quotes([row("iPhone 17", "256", "A", 120000)])
    assert summary["runner_up_price"] is None and summary["best_vs_retail"] is None


def test_quote_limits_the_ranking():
    rows = [row("iPhone 17", "256", f"S{index}", 100000 + index) for index in range(10)]
    assert len(summarise_quotes(rows)["ranking"]) == 5
    assert len(summarise_quotes(rows, top=10)["ranking"]) == 10


def test_quote_of_nothing():
    assert summarise_quotes([]) == {"store_count": 0}


# ---------------------------------------------------------------------------
# trend
# ---------------------------------------------------------------------------

TODAY = date(2026, 11, 4)


def days(*pairs):
    return [(TODAY - timedelta(days=ago), price) for ago, price in pairs]


def test_trend_down():
    trend = summarise_trend(days((30, 220000), (14, 212000), (7, 210000), (0, 200000)), TODAY)
    assert trend["direction"] == "down"
    assert trend["change_7d"] == {"from_date": "2026-10-28", "from_price": 210000, "change": -10000, "percent": -4.8}
    assert trend["change_30d"]["change"] == -20000
    assert trend["slope_per_week"] < 0
    assert (trend["high_30d"], trend["low_30d"]) == (220000, 200000)
    assert trend["latest_price"] == 200000


def test_trend_up_and_flat():
    assert summarise_trend(days((7, 100000), (0, 104000)), TODAY)["direction"] == "up"
    assert summarise_trend(days((7, 100000), (0, 100900)), TODAY)["direction"] == "flat"
    assert summarise_trend(days((7, 100000), (0, 99000)), TODAY)["direction"] == "down"  # exactly -1 % is a move
    assert summarise_trend(days((7, 100000), (0, 99040)), TODAY)["direction"] == "flat"  # -0.96 %, shown as -1.0


def test_trend_uses_the_closest_earlier_day():
    trend = summarise_trend(days((9, 100000), (5, 102000), (0, 103000)), TODAY)
    assert trend["change_7d"]["from_price"] == 100000  # 9 days ago is the last day on or before 7 days ago


def test_trend_without_enough_history():
    trend = summarise_trend(days((0, 100000)), TODAY)
    assert trend["direction"] == "unknown"
    assert trend["change_7d"] is None and trend["slope_per_week"] is None
    assert summarise_trend([], TODAY) == {"days_of_data": 0, "direction": "unknown"}


def test_trend_ignores_future_and_zero_prices_and_keeps_last_duplicate():
    trend = summarise_trend([(TODAY + timedelta(days=1), 999999), (TODAY, 0), (TODAY - timedelta(days=1), 5),
                             (TODAY - timedelta(days=1), 100000)], TODAY)
    assert trend["latest_price"] == 100000
    assert trend["days_of_data"] == 1


def test_weekly_slope_of_a_straight_line():
    series = [(TODAY - timedelta(days=ago), 100000 - 1000 * (10 - ago)) for ago in range(10, -1, -1)]
    assert weekly_slope(series) == -7000


def test_no_slope_for_less_than_two_weeks_of_history():
    assert summarise_trend(days((10, 110000), (7, 105000), (0, 100000)), TODAY)["slope_per_week"] is None
    assert summarise_trend(days((14, 110000), (7, 105000), (0, 100000)), TODAY)["slope_per_week"] == -5000


def test_weekly_slope_needs_three_points():
    assert weekly_slope(days((1, 1), (0, 2))) is None


# ---------------------------------------------------------------------------
# overseas
# ---------------------------------------------------------------------------

MARKET_ROWS = [
    {"market": "hk", "model": "iPhone 17 Pro", "capacity": "256", "color_code": "silver", "price": 10500, "currency": "HKD", "offers": 1},
    {"market": "hk", "model": "iPhone 17 Pro", "capacity": "256", "color_code": "deep-blue", "price": 10800, "currency": "HKD", "offers": 2},
    {"market": "us", "model": "iPhone 17 Pro", "capacity": "256", "color_code": None, "price": 1000, "currency": "USD", "offers": 5},
    {"market": "us", "model": "iPhone 17 Pro", "capacity": "512", "color_code": None, "price": 1200, "currency": "USD", "offers": 5},
]


def test_to_yen():
    assert to_yen(100, "USD", RATES) == 15000
    assert to_yen(100, "JPY", RATES) == 100
    assert to_yen(100, "EUR", RATES) is None
    assert to_yen(None, "USD", RATES) is None


def test_best_overseas_per_market():
    best = best_overseas(MARKET_ROWS, "iPhone 17 Pro", "256")
    assert best["hk"] == {"price": 10800, "currency": "HKD", "color": "deep-blue", "buyers": 3}
    assert best["us"]["price"] == 1000


def test_compare_markets_sorted_by_yen():
    result = compare_markets(208000, best_overseas(MARKET_ROWS, "iPhone 17 Pro", "256"), RATES)
    assert [item["market"] for item in result] == ["hk", "us"]
    hk = result[0]
    assert hk["price_jpy"] == 216000
    assert hk["vs_japan"] == 8000
    assert hk["vs_japan_percent"] == 3.8
    assert result[1]["vs_japan"] == 150000 - 208000


def test_compare_markets_without_rates_or_japan_price():
    result = compare_markets(None, best_overseas(MARKET_ROWS, "iPhone 17 Pro", "256"), {})
    assert all(item["price_jpy"] is None and "vs_japan" not in item for item in result)


# ---------------------------------------------------------------------------
# bulk
# ---------------------------------------------------------------------------

def test_bulk_total_and_single_store_option():
    lines = [
        {"model": "iPhone 17 Pro", "capacity": "256", "quantity": 2, "best_price": 208000, "best_store": "森森買取",
         "ranking_all": [{"store": "森森買取", "price": 208000}, {"store": "アキモバ", "price": 206000}]},
        {"model": "iPhone 16e", "capacity": "128", "quantity": 3, "best_price": 82000, "best_store": "森森買取",
         "ranking_all": [{"store": "森森買取", "price": 82000}, {"store": "アキモバ", "price": 80000}]},
    ]
    total = bulk_total(lines)
    assert total["total"] == 2 * 208000 + 3 * 82000
    assert total["phones"] == 5
    assert total["single_store"] == {"store": "森森買取", "total": total["total"], "difference": 0}


def test_bulk_single_store_must_quote_every_line():
    lines = [
        {"model": "a", "capacity": "1", "quantity": 1, "best_price": 10, "best_store": "X", "ranking_all": [{"store": "X", "price": 10}]},
        {"model": "b", "capacity": "1", "quantity": 1, "best_price": 10, "best_store": "Y", "ranking_all": [{"store": "Y", "price": 10}]},
    ]
    assert bulk_total(lines)["single_store"] is None


def test_bulk_needs_two_phones():
    assert bulk_total([{"model": "a", "capacity": "1", "quantity": 1, "best_price": 10, "best_store": "X"}]) is None
    assert bulk_total([]) is None


# ---------------------------------------------------------------------------
# builder
# ---------------------------------------------------------------------------

def evidence(message, **kwargs):
    return build_price_evidence(understand(message).to_dict(), PRICE_ROWS, fx_rates=RATES, today=TODAY, **kwargs)


def test_evidence_for_one_phone():
    result = evidence("iPhone 17 Pro 256GB はいくら？", market_rows=MARKET_ROWS,
                      daily_best={("iPhone 17 Pro", "256"): days((7, 210000), (0, 208000))})
    assert result["version"] == "evidence-v1"
    assert result["intent"] == "price_quote"
    assert result["has_prices"] is True
    item = result["items"][0]
    assert item["model"] == "iPhone 17 Pro" and item["notes"] == []
    entry = item["capacities"][0]
    assert entry["quotes"]["best_store"] == "森森買取"
    assert entry["trend"]["direction"] == "flat"
    assert entry["overseas"][0]["market"] == "hk"
    assert result["bulk"] is None


def test_evidence_lists_capacities_when_none_was_asked():
    item = evidence("17 pro いくら")["items"][0]
    assert [entry["capacity"] for entry in item["capacities"]] == ["256", "512"]
    assert item["notes"] == ["capacity_missing"]


def test_evidence_bulk_quote():
    result = evidence("17 pro 256 x2 と 16e 128 x3 合計")
    assert result["bulk"]["total"] == 2 * 208000 + 3 * 82000
    assert result["bulk"]["single_store"]["store"] == "森森買取"
    assert result["bulk"]["excluded"] == []


def test_bulk_reports_phones_it_could_not_price():
    result = evidence("17 pro x2 と 16e 128 x3 と iPhone 12 x1 合計")
    assert result["bulk"]["total"] == 3 * 82000
    assert result["bulk"]["excluded"] == [
        {"model": "iPhone 17 Pro", "capacity": None, "quantity": 2, "reason": "capacity_missing"},
        {"model": "iPhone 12", "capacity": None, "quantity": 1, "reason": "unknown_model"},
    ]


def test_no_total_for_a_plain_comparison():
    assert evidence("17 pro 256 と 16e 128 どっちが高い？")["bulk"] is None


def test_devices_beyond_the_limit_are_listed():
    message = " ".join(f"iphone {generation} 256" for generation in range(11, 18))
    assert evidence(message)["devices_not_shown"] == ["iPhone 15", "iPhone 16", "iPhone 17"]


def test_evidence_for_unknown_and_missing_models():
    result = evidence("iPhone 12 64 と 17 air 256 いくら")
    assert [item["notes"] for item in result["items"]] == [["unknown_model"], ["no_prices"]]
    assert result["has_prices"] is False


def test_evidence_follow_up_and_no_devices():
    result = evidence("那 512 呢？")
    assert result["items"] == [] and result["follow_up_capacity"] == "512"


def test_evidence_keeps_colour_condition_and_quantity_of_the_question():
    item = evidence("iPhone Duo 1TB ナイトスカイ 未開封 2台")["items"][0]
    assert (item["color"], item["condition"], item["quantity"]) == ("night-sky", "sealed", 2)
    assert item["capacities"][0]["quotes"]["best_vs_retail"] == 491000 - 469800


def test_evidence_limits_the_number_of_devices():
    message = " ".join(f"iphone {generation} 256" for generation in range(11, 18))
    assert len(evidence(message)["items"]) == 4


# ---------------------------------------------------------------------------
# database loaders
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_daily_best_uses_each_stores_last_quote_and_drops_outliers():
    day = datetime(2026, 11, 4, 10, 0)
    points = [
        (1, day, 200000), (1, day + timedelta(hours=3), 201000),  # store 1 updated later that day
        (2, day, 199000), (3, day, 198000),
        (4, day, 260000),  # far above the others: rejected by the consensus band
        (5, day, 5000),  # below the floor
    ]
    assert daily_best_from_history(points, ceiling=1_000_000) == [(date(2026, 11, 4), 201000)]


def test_daily_best_without_enough_stores_keeps_every_quote():
    day = datetime(2026, 11, 4, 10, 0)
    assert daily_best_from_history([(1, day, 200000), (2, day, 260000)], ceiling=1_000_000) == [(date(2026, 11, 4), 260000)]


def test_daily_best_respects_the_ceiling_and_japan_days():
    late_utc = datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc)  # 01:00 on 11/4 in Japan
    points = [(1, late_utc, 200000), (2, late_utc, 9_999_999)]
    assert daily_best_from_history(points, ceiling=600000) == [(date(2026, 11, 4), 200000)]


def seed_history(db, model="iPhone 17 Pro", capacity="256", by_day=None, retail=219800):
    product = Product(name=f"{model} {capacity}", model=model, capacity=capacity, retail_price=retail)
    stores = [Store(name=f"店{index}") for index in range(3)]
    db.add(product)
    db.add_all(stores)
    db.commit()
    for days_ago, prices in (by_day or {}).items():
        when = datetime.combine(date.today() - timedelta(days=days_ago), datetime.min.time()) + timedelta(hours=12)
        for store, price in zip(stores, prices):
            db.add(PriceHistory(product_id=product.id, store_id=store.id, price=price, recorded_at=when))
    db.commit()
    return product


def test_load_daily_best_reads_price_history(db):
    seed_history(db, by_day={8: (210000, 209000, 208000), 0: (200000, 199000, 260000), 60: (250000, 250000, 250000)})
    series = load_daily_best(db, {("iPhone 17 Pro", "256")})
    assert series == {("iPhone 17 Pro", "256"): [(date.today() - timedelta(days=8), 210000), (date.today(), 200000)]}
    assert load_daily_best(db, set()) == {}


def test_past_days_are_cached_and_only_today_is_read_again(db):
    product = seed_history(db, by_day={3: (210000, 209000, 208000), 0: (200000, 199000, 198000)})
    first = load_daily_best(db, {("iPhone 17 Pro", "256")})[("iPhone 17 Pro", "256")]
    assert len(PAST_DAYS_CACHE) == 1
    # a change to an old day is not seen while cached, a new quote today is
    old_day = datetime.combine(date.today() - timedelta(days=3), datetime.min.time()) + timedelta(hours=13)
    db.add(PriceHistory(product_id=product.id, store_id=1, price=215000, recorded_at=old_day))
    db.add(PriceHistory(product_id=product.id, store_id=1, price=203000,
                        recorded_at=datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=13)))
    db.commit()
    second = load_daily_best(db, {("iPhone 17 Pro", "256")})[("iPhone 17 Pro", "256")]
    assert second[0] == first[0]
    assert second[-1] == (date.today(), 203000)
    assert PAST_DAYS_CACHE.hits == 1


def test_load_daily_best_merges_capacity_spellings(db):
    seed_history(db, capacity="256GB", by_day={0: (200000, 199000, 198000)})
    assert load_daily_best(db, {("iPhone 17 Pro", "256")})[("iPhone 17 Pro", "256")][-1][1] == 200000


def test_load_market_snapshots_uses_the_latest_fresh_snapshot(db):
    now = datetime.now(timezone.utc)
    common = {"market": "hk", "source": "debitbaba", "model": "iPhone 17 Pro", "capacity": "256", "currency": "HKD"}
    db.add_all([
        MarketPrice(**common, color_code="silver", price=10000, collected_at=now - timedelta(hours=5)),
        MarketPrice(**common, color_code="silver", price=10500, collected_at=now - timedelta(hours=1)),
        MarketPrice(**{**common, "source": "old"}, color_code="silver", price=99999, collected_at=now - timedelta(days=5)),
        MarketPrice(**{**common, "model": "iPhone 16"}, color_code=None, price=5000, collected_at=now - timedelta(hours=1)),
    ])
    db.commit()
    rows = load_market_snapshots(db, {"iPhone 17 Pro"})
    assert [(item["source"], item["price"]) for item in rows] == [("debitbaba", 10500)]
    assert load_market_snapshots(db, set()) == []


def test_collect_price_evidence_reads_the_database(db):
    seed_history(db, by_day={7: (210000, 209000, 208000), 0: (200000, 199000, 198000)})
    result = collect_price_evidence(db, understand("17 pro 256 いくら").to_dict(), PRICE_ROWS, RATES, "2026-11-04T10:00:00")
    assert result["items"][0]["capacities"][0]["trend"]["direction"] == "down"
    assert result["fx_updated"] == "2026-11-04T10:00:00"


def test_collect_price_evidence_never_raises():
    class Broken:
        def query(self, *args, **kwargs):
            raise RuntimeError("database down")

    assert collect_price_evidence(Broken(), understand("17 pro 256 いくら").to_dict(), PRICE_ROWS) == {}
