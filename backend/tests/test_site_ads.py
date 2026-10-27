import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import SiteAd
from app.db.session import Base, get_db
from app.db.site_ads import import_ads
from app.web.routers import ads

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(ads.router, prefix="/api/v1")
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def ad(key, **extra):
    return {"slot": "ai_home", "key": key, "icon": "phone", "brand": f"Brand {key}",
            "text": {"ja": "日本語", "zh": "中文", "en": "English"},
            "href": f"https://example.com/{key}", **extra}


def test_import_replaces_the_whole_slot_and_api_lists_enabled_ads_in_order():
    with TestingSessionLocal() as db:
        import_ads(db, [ad("old")])
        result = import_ads(db, [ad("b", sort_order=2), ad("a", sort_order=1), ad("off", enabled=False)])
    assert result == {"slots": ["ai_home"], "removed": 1, "imported": 3}

    response = TestClient(app).get("/api/v1/ads", params={"slot": "ai_home"})
    assert response.status_code == 200
    body = response.json()
    assert [item["key"] for item in body["ads"]] == ["a", "b"]
    assert body["ads"][0]["text"] == {"ja": "日本語", "zh": "中文", "en": "English"}
    assert "max-age" in response.headers["cache-control"]


def test_other_slots_are_untouched_and_unknown_slot_is_empty():
    with TestingSessionLocal() as db:
        import_ads(db, [ad("keep", slot="prices_top")])
        import_ads(db, [ad("a")])
        assert db.query(SiteAd).count() == 2
    assert TestClient(app).get("/api/v1/ads", params={"slot": "nowhere"}).json()["ads"] == []


@pytest.mark.parametrize("href", ["javascript:alert(1)", "http://example.com/", "//example.com/", ""])
def test_import_rejects_unsafe_links_without_changing_the_table(href):
    with TestingSessionLocal() as db:
        import_ads(db, [ad("a")])
        with pytest.raises(ValueError):
            import_ads(db, [ad("b"), ad("bad", href=href)])
        assert [row.key for row in db.query(SiteAd)] == ["a"]


def test_api_drops_unsafe_rows_written_directly_to_the_table():
    with TestingSessionLocal() as db:
        db.add(SiteAd(slot="ai_home", key="x", icon="link", brand="X", text_ja="x", text_zh="x", text_en="x",
                      href="javascript:alert(1)"))
        db.commit()
    assert TestClient(app).get("/api/v1/ads", params={"slot": "ai_home"}).json()["ads"] == []


def test_slot_name_is_validated():
    assert TestClient(app).get("/api/v1/ads", params={"slot": "../etc"}).status_code == 422


def test_import_requires_all_languages_and_known_icon():
    with TestingSessionLocal() as db:
        with pytest.raises(ValueError):
            import_ads(db, [ad("a", text={"ja": "x", "zh": "", "en": "x"})])
        with pytest.raises(ValueError):
            import_ads(db, [ad("a", icon="logo")])
