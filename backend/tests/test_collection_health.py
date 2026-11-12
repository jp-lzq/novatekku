"""Health of collection sources: failing streaks, stale sources, empty pages."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import CollectionRun, CollectionSource
from app.db.session import Base, get_db
from app.web.routers import admin
from app.web.routers.members import require_admin
from app.web.services.collection_health import RunSnapshot, assess, summarise

NOW = datetime(2026, 11, 12, 6, 0, tzinfo=timezone.utc)


def run(status, hours_ago, pages=8, empty=0):
    return RunSnapshot(status, NOW - timedelta(hours=hours_ago), {"pages_total": pages, "empty_pages": empty})


def test_healthy():
    health = assess([run("success", 1), run("success", 2), run("failed", 3)], now=NOW)
    assert health.state == "healthy" and health.reasons == []
    assert health.consecutive_failures == 0
    assert health.success_rate == pytest.approx(2 / 3)


def test_failing_after_three_failures_in_a_row():
    health = assess([run("failed", 1), run("failed", 2), run("failed", 3), run("success", 4)], now=NOW)
    assert health.state == "failing"
    assert health.consecutive_failures == 3
    assert health.reasons == ["3回連続で失敗"]


def test_two_failures_are_not_yet_failing():
    assert assess([run("failed", 1), run("failed", 2), run("success", 3)], now=NOW).state != "failing"


def test_stale_when_nothing_succeeded_for_a_day():
    health = assess([run("failed", 1), run("partial", 30)], now=NOW)
    assert health.state == "stale"


def test_degraded_by_low_success_rate():
    runs = [run("success", 1), run("failed", 2), run("failed", 3), run("success", 4), run("failed", 5), run("failed", 6)]
    health = assess(runs, now=NOW)
    assert health.state == "degraded"
    assert "成功率 33%" in health.reasons[0]


def test_degraded_when_successful_runs_have_mostly_empty_pages():
    """The 買取ソムリエ case: 'success' with 7 of 8 pages empty."""
    health = assess([run("success", 1, pages=8, empty=7), run("success", 2, pages=8, empty=7)], now=NOW)
    assert health.state == "degraded"
    assert health.empty_page_ratio == pytest.approx(7 / 8)
    assert "88% のページが空" in health.reasons[0]


def test_special_states():
    assert assess([], now=NOW).state == "unknown"
    assert assess([run("unsupported", 1)], now=NOW).state == "unknown"
    assert assess([run("failed", 1)] * 5, enabled=False, now=NOW).state == "disabled"
    assert assess([], unsupported=True, now=NOW).state == "unsupported"


def test_naive_timestamps_and_text_detail():
    snapshot = RunSnapshot.from_row("success", datetime(2026, 11, 12, 5, 0), json.dumps({"pages_total": 2, "empty_pages": 0}))
    assert assess([snapshot], now=NOW).state == "healthy"
    assert RunSnapshot.from_row("failed", NOW, "not json").detail == {}
    assert RunSnapshot.from_row("failed", NOW, None).detail == {}


def test_summary_counts_every_state():
    counts = summarise(["healthy", "failing", "healthy"])
    assert counts["healthy"] == 2 and counts["failing"] == 1 and counts["stale"] == 0


def test_to_dict_is_json_ready():
    json.dumps(assess([run("success", 1)], now=NOW).to_dict())


# ---------------------------------------------------------------------------
# admin endpoint
# ---------------------------------------------------------------------------

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def test_collection_sources_include_health():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    db.add_all([
        CollectionSource(kind="official", name="A 公式", store_name="A", parser="a", urls="[]"),
        CollectionSource(kind="official", name="B 公式", store_name="B", parser="b", urls="[]"),
        CollectionSource(kind="market", name="香港 X", parser="x", urls="[]", options='{"market": "hk"}'),
    ])
    now = datetime.now(timezone.utc)
    for hours in (1, 2, 3):
        db.add(CollectionRun(source_type="official", source_name="A 公式", store_name="A", status="failed",
                             started_at=now - timedelta(hours=hours)))
    db.add(CollectionRun(source_type="official", source_name="B 公式", store_name="B", status="success",
                         started_at=now - timedelta(hours=1), detail=json.dumps({"pages_total": 4, "empty_pages": 0})))
    db.add(CollectionRun(source_type="market_hk", source_name="香港 X", status="success",
                         started_at=now - timedelta(hours=1), detail="{}"))
    db.commit()
    db.close()

    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = lambda: object()
    body = TestClient(app).get("/api/v1/admin/collection-sources").json()
    health = {item["name"]: item["health"]["state"] for item in body["items"]}
    assert health == {"A 公式": "failing", "B 公式": "healthy", "香港 X": "healthy"}
    assert body["health_summary"]["failing"] == 1 and body["health_summary"]["healthy"] == 2
