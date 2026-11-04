"""Rendered evidence lines and the admin-only AI preview endpoint."""

from datetime import date, timedelta

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai_gateway import router as ai_router
from app.ai_gateway.evidence import build_price_evidence
from app.ai_gateway.evidence.render import capacity_label, money, percent, render_evidence, yen
from app.ai_gateway.understanding import understand
from app.db.session import Base, get_db
from app.web.routers.members import get_auth_context, require_admin

RATES = {"USD": {"rate": 150.0}, "HKD": {"rate": 20.0}}
TODAY = date(2026, 11, 4)
ROWS = [
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "森森買取", "price": 208000, "retail_price": 219800},
    {"model": "iPhone 17 Pro", "capacity": "256", "store": "アキモバ", "price": 206000, "retail_price": 219800},
    {"model": "iPhone 16e", "capacity": "128", "store": "アキモバ", "price": 82000},
]
MARKETS = [{"market": "hk", "model": "iPhone 17 Pro", "capacity": "256", "color_code": "silver", "price": 10800,
            "currency": "HKD", "offers": 1}]
DAILY = {("iPhone 17 Pro", "256"): [(TODAY - timedelta(days=7), 210000), (TODAY - timedelta(days=3), 209000), (TODAY, 208000)]}


def evidence(message):
    return build_price_evidence(understand(message).to_dict(), ROWS, daily_best=DAILY, market_rows=MARKETS,
                                fx_rates=RATES, today=TODAY)


@pytest.mark.parametrize("value,signed,expected", [
    (208000, False, "¥208,000"), (-11800, True, "-¥11,800"), (2000, True, "+¥2,000"), (0, True, "±¥0"), (None, False, "-"),
])
def test_yen(value, signed, expected):
    assert yen(value, signed) == expected


def test_money_percent_and_capacity():
    assert money(10800, "HKD") == "HK$10,800"
    assert money(1000, "USD") == "$1,000"
    assert money(5, "EUR") == "EUR 5"
    assert percent(-5.4) == " (-5.4%)" and percent(None) == ""
    assert capacity_label("256") == "256GB" and capacity_label("1TB") == "1TB"


def test_japanese_line_has_every_fact():
    line = render_evidence(evidence("17 pro 256 いくら"), "ja")[0]
    assert line.startswith("iPhone 17 Pro 256GB: 最高 ¥208,000 (森森買取)")
    for part in ("2位 ¥206,000", "2店", "定価比 -¥11,800 (-5.4%)", "7日前比 -¥2,000 (-1.0%) 横ばい",
                 "香港 HK$10,800 = ¥216,000 日本比 +¥8,000 (+3.8%)"):
        assert part in line


def test_chinese_and_english_lines():
    assert "最高 ¥208,000" in render_evidence(evidence("17 pro 256 多少钱"), "zh")[0]
    assert "比官网价" in render_evidence(evidence("17 pro 256 多少钱"), "zh")[0]
    english = render_evidence(evidence("how much is iphone 17 pro 256"), "en")[0]
    assert "best ¥208,000" in english and "Hong Kong HK$10,800" in english


def test_unknown_language_falls_back_to_english():
    assert "best" in render_evidence(evidence("17 pro 256"), "fr")[0]


def test_notes_are_rendered():
    lines = render_evidence(evidence("iPhone 12 64 と 17 air 256 と 17 pro 1tb いくら"), "ja")
    assert lines[0] == "iPhone 12: NOVA の対象外の機種です"
    assert lines[1] == "iPhone 17 Air: 現在この機種の買取価格はありません"
    assert lines[2] == "iPhone 17 Pro 1TB: この容量の価格はありません（他の容量を表示）"
    assert lines[3].startswith("iPhone 17 Pro 256GB:")


def test_bulk_line():
    lines = render_evidence(evidence("17 pro 256 x2 と 16e 128 x3"), "ja")
    assert lines[-1] == "合計 ¥662,000 (5台) / 1店でまとめて売るなら アキモバ ¥658,000"


def test_excluded_and_not_shown_lines():
    lines = render_evidence(evidence("17 pro x2 と 16e 128 x3 と iPhone 12 x1 合計"), "ja")
    assert "iPhone 17 Pro ×2 は容量が分からないため合計に含めていません" in lines
    assert "iPhone 12 ×1 は価格がないため合計に含めていません" in lines
    many = " ".join(f"iphone {generation} 256" for generation in range(11, 18))
    assert render_evidence(evidence(many), "en")[-1] == "also asked: iPhone 15, iPhone 16, iPhone 17; at most 4 models are handled at once"


def test_written_capacity_without_price_is_named_in_the_exclusion():
    lines = render_evidence(evidence("17 pro 1tb x2 と 16e 128 x1 合計"), "ja")
    assert "iPhone 17 Pro 1TB ×2 はこの容量の価格がないため合計に含めていません" in lines


def test_follow_up_line():
    assert render_evidence(evidence("那 512 呢？"), "zh") == ["请按上一个问题的机型回答 512GB"]


def test_lines_are_attached_in_three_languages():
    result = evidence("17 pro 256")
    assert set(result["lines"]) == {"ja", "zh", "en"}
    assert result["lines"]["ja"] == render_evidence(result, "ja")


def test_empty_evidence_renders_nothing():
    assert render_evidence({}, "ja") == []


# ---------------------------------------------------------------------------
# admin preview endpoint
# ---------------------------------------------------------------------------

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def app():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    application = FastAPI()
    application.include_router(ai_router.router, prefix="/api/v1")
    application.dependency_overrides[get_db] = override_get_db
    return application


def test_preview_requires_login(app):
    def not_logged_in():
        raise HTTPException(status_code=401, detail="Authentication required")

    app.dependency_overrides[get_auth_context] = not_logged_in
    assert TestClient(app).get("/api/v1/ai/preview", params={"message": "17 pro"}).status_code == 401


def test_preview_rejects_members_who_are_not_admins(app):
    def member_only():
        raise HTTPException(status_code=403, detail="Administrator access required")

    app.dependency_overrides[require_admin] = member_only
    assert TestClient(app).get("/api/v1/ai/preview", params={"message": "17 pro"}).status_code == 403


def test_preview_for_admin(app):
    app.dependency_overrides[require_admin] = lambda: object()
    client = TestClient(app)
    body = client.get("/api/v1/ai/preview", params={"message": "17プロマ 256 どこが一番高い？", "language": "ja"}).json()
    assert body["understanding"]["intent"] == "store_ranking"
    assert body["understanding"]["devices"][0]["model"] == "iPhone 17 Pro Max"
    assert body["price_evidence"]["items"][0]["notes"] == ["no_prices"]  # empty database
    assert body["lines"] == ["iPhone 17 Pro Max: 現在この機種の買取価格はありません"]


@pytest.mark.parametrize("params", [{"message": ""}, {"message": "x" * 2001}, {"message": "17", "language": "fr"}])
def test_preview_validates_input(app, params):
    app.dependency_overrides[require_admin] = lambda: object()
    assert TestClient(app).get("/api/v1/ai/preview", params=params).status_code == 422
