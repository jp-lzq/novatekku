from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.db.models import (
    AIConversationLog,
    CollectionRun,
    Member,
    MemberLoginEvent,
    OfficialStoreProduct,
    Price,
    PriceCollectionSource,
    Product,
    Store,
)
from app.ai_gateway import core as ai_core
from app.ai_gateway import router as ai
from app.web.routers import admin, members, products
from app.web.services.auth_security import auth_rate_limiter
from app.pricing.product_catalog import rebuild_standard_price_index


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(members.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    auth_rate_limiter.reset_for_tests()
    monkeypatch.setattr(settings, "redis_url", "")
    monkeypatch.setattr(settings, "auth_cookie_secure", True)
    monkeypatch.setattr(settings, "auth_origins", "https://testserver")
    monkeypatch.setattr(settings, "public_member_auth_enabled", True)
    monkeypatch.setattr(settings, "ai_core_module", "")
    monkeypatch.setattr(settings, "admin_username", "siteadmin")
    ai_core._load_core.cache_clear()


@pytest.fixture
def client():
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def register(client: TestClient, username="normal", email="normal@example.com"):
    return client.post(
        "/api/v1/members/register",
        json={"username": username, "email": email, "password": "StrongPass123"},
    )


def csrf_headers(client: TestClient):
    return {"X-NOVA-CSRF": client.cookies.get("nova_csrf")}


def test_session_is_server_side_and_survives_navigation(client):
    response = register(client)
    assert response.status_code == 201
    session_cookie = next(value for value in response.headers.get_list("set-cookie") if value.startswith("nova_session="))
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert client.get("/api/v1/members/me").json()["username"] == "normal"
    assert client.get("/api/v1/admin/overview").status_code == 403


def test_login_accepts_username_or_email(client):
    assert register(client).status_code == 201
    assert client.post("/api/v1/members/logout", headers=csrf_headers(client)).status_code == 200
    username_login = client.post(
        "/api/v1/members/login",
        json={"identifier": "NORMAL", "password": "StrongPass123"},
    )
    assert username_login.status_code == 200
    assert client.post("/api/v1/members/logout", headers=csrf_headers(client)).status_code == 200
    email_login = client.post(
        "/api/v1/members/login",
        json={"identifier": "NORMAL@EXAMPLE.COM", "password": "StrongPass123"},
    )
    assert email_login.status_code == 200

    with TestingSessionLocal() as db:
        events = db.query(MemberLoginEvent).order_by(MemberLoginEvent.id).all()
        assert [event.event_type for event in events] == ["register", "login", "login"]
        assert all(event.created_at is not None for event in events)


def test_auth_pause_blocks_public_registration_and_login_but_keeps_admin_access(client, monkeypatch):
    monkeypatch.setattr(settings, "public_member_auth_enabled", False)
    registration = register(client)
    assert registration.status_code == 503
    assert registration.headers["retry-after"] == "3600"

    with TestingSessionLocal() as db:
        db.add_all([
            Member(username="normal", email="normal@example.com", password_hash=members.hash_password("StrongPass123")),
            Member(username="siteadmin", email="admin@example.com", password_hash=members.hash_password("AdminPass123")),
        ])
        db.commit()

    normal_login = client.post(
        "/api/v1/members/login",
        json={"identifier": "normal", "password": "StrongPass123"},
    )
    assert normal_login.status_code == 503
    assert normal_login.headers["retry-after"] == "3600"
    assert client.post(
        "/api/v1/members/login",
        json={"identifier": "siteadmin", "password": "AdminPass123"},
    ).status_code == 200


def test_admin_can_pause_and_restore_member_auth(client):
    with TestingSessionLocal() as db:
        db.add_all([
            Member(username="normal", email="normal@example.com", password_hash=members.hash_password("StrongPass123")),
            Member(username="siteadmin", email="admin@example.com", password_hash=members.hash_password("AdminPass123")),
        ])
        db.commit()

    assert client.get("/api/v1/members/auth-status").json() == {"enabled": True}
    assert client.post(
        "/api/v1/members/login",
        json={"identifier": "siteadmin", "password": "AdminPass123"},
    ).status_code == 200

    missing_csrf = client.post("/api/v1/admin/member-auth", json={"enabled": False})
    assert missing_csrf.status_code == 403
    paused = client.post(
        "/api/v1/admin/member-auth",
        headers=csrf_headers(client),
        json={"enabled": False},
    )
    assert paused.status_code == 200
    assert paused.json()["enabled"] is False
    assert paused.json()["updated_by"] == "siteadmin"
    assert client.get("/api/v1/members/auth-status").json() == {"enabled": False}

    assert client.post("/api/v1/members/logout", headers=csrf_headers(client)).status_code == 200
    assert client.post(
        "/api/v1/members/login",
        json={"identifier": "normal", "password": "StrongPass123"},
    ).status_code == 503
    assert client.post(
        "/api/v1/members/login",
        json={"identifier": "siteadmin", "password": "AdminPass123"},
    ).status_code == 200

    restored = client.post(
        "/api/v1/admin/member-auth",
        headers=csrf_headers(client),
        json={"enabled": True},
    )
    assert restored.status_code == 200
    assert restored.json()["enabled"] is True
    assert client.post("/api/v1/members/logout", headers=csrf_headers(client)).status_code == 200
    assert client.post(
        "/api/v1/members/login",
        json={"identifier": "normal", "password": "StrongPass123"},
    ).status_code == 200
    assert client.get("/api/v1/admin/member-auth").status_code == 403
    assert client.post(
        "/api/v1/admin/member-auth",
        headers=csrf_headers(client),
        json={"enabled": False},
    ).status_code == 403


def test_logout_requires_csrf_and_bad_login_does_not_enumerate(client):
    assert register(client).status_code == 201
    assert client.post("/api/v1/members/logout").status_code == 403
    wrong = client.post(
        "/api/v1/members/login",
        json={"identifier": "normal", "password": "WrongPass123"},
    )
    unknown = client.post(
        "/api/v1/members/login",
        json={"identifier": "missing", "password": "WrongPass123"},
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    with TestingSessionLocal() as db:
        assert db.query(MemberLoginEvent).count() == 1


def test_auth_rejects_untrusted_browser_origin(client):
    response = client.post(
        "/api/v1/members/login",
        headers={"Origin": "https://attacker.example"},
        json={"identifier": "normal", "password": "StrongPass123"},
    )
    assert response.status_code == 403


def test_legacy_unverified_password_reset_is_disabled(client):
    assert register(client).status_code == 201
    response = client.post(
        "/api/v1/members/reset-password",
        json={"email": "normal@example.com", "password": "AttackerPass123"},
    )
    assert response.status_code == 410


def test_password_reset_is_single_use_and_revokes_sessions(client, monkeypatch):
    assert register(client).status_code == 201
    captured: dict[str, str] = {}

    def capture_reset_email(recipient: str, token: str):
        captured["recipient"] = recipient
        captured["token"] = token

    monkeypatch.setattr(settings, "password_reset_email_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@example.com")
    monkeypatch.setattr(settings, "public_app_url", "https://testserver")
    monkeypatch.setattr(members, "send_password_reset_email", capture_reset_email)

    known = client.post("/api/v1/members/password-reset/request", json={"email": "normal@example.com"})
    unknown = client.post("/api/v1/members/password-reset/request", json={"email": "unknown@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert captured["recipient"] == "normal@example.com"

    confirmed = client.post(
        "/api/v1/members/password-reset/confirm",
        json={"token": captured["token"], "password": "NewStrongPass123"},
    )
    assert confirmed.status_code == 200
    assert client.get("/api/v1/members/me").status_code == 401
    reused = client.post(
        "/api/v1/members/password-reset/confirm",
        json={"token": captured["token"], "password": "AnotherPass123"},
    )
    assert reused.status_code == 400


def test_login_rate_limit_returns_retry_after(client):
    for _ in range(10):
        response = client.post(
            "/api/v1/members/login",
            json={"identifier": "rate-limit", "password": "WrongPass123"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/members/login",
        json={"identifier": "rate-limit", "password": "WrongPass123"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == str(settings.auth_rate_limit_window_seconds)


def test_siteadmin_is_admin_without_changing_credentials(client):
    legacy_hash = members.hash_password("AdminPass123").replace("$600000$", "$120000$", 1)
    # Make a valid legacy digest rather than asking login to rewrite it.
    salt = legacy_hash.split("$")[2]
    import hashlib
    digest = hashlib.pbkdf2_hmac("sha256", b"AdminPass123", salt.encode(), 120_000).hex()
    legacy_hash = f"pbkdf2_sha256$120000${salt}${digest}"
    with TestingSessionLocal() as db:
        db.add(Member(username="siteadmin", email="admin@example.com", password_hash=legacy_hash))
        db.commit()

    product_payload = {"name": "iPhone test 128", "model": "iPhone test", "capacity": "128"}
    assert client.post("/api/v1/products", json=product_payload).status_code == 401

    login = client.post(
        "/api/v1/members/login",
        json={"identifier": "siteadmin", "password": "AdminPass123"},
    )
    assert login.status_code == 200
    assert login.json()["is_admin"] is True
    assert client.get("/api/v1/admin/overview").status_code == 200
    assert client.post("/api/v1/products", json=product_payload).status_code == 403
    created = client.post("/api/v1/products", headers=csrf_headers(client), json=product_payload)
    assert created.status_code == 200
    assert created.json()["name"] == product_payload["name"]
    with TestingSessionLocal() as db:
        assert db.query(Member).filter(Member.username == "siteadmin").one().password_hash == legacy_hash


def test_admin_can_update_email_but_not_reserved_username(client):
    with TestingSessionLocal() as db:
        db.add(Member(
            username="siteadmin",
            email="admin@example.com",
            password_hash=members.hash_password("AdminPass123"),
        ))
        db.commit()

    assert client.post(
        "/api/v1/members/login",
        json={"identifier": "siteadmin", "password": "AdminPass123"},
    ).status_code == 200

    renamed = client.post(
        "/api/v1/members/profile",
        headers=csrf_headers(client),
        json={
            "username": "new-admin",
            "email": "admin@example.com",
            "current_password": "AdminPass123",
        },
    )
    assert renamed.status_code == 422

    updated = client.post(
        "/api/v1/members/profile",
        headers=csrf_headers(client),
        json={
            "username": "siteadmin",
            "email": "new-admin@example.com",
            "current_password": "AdminPass123",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == "siteadmin"
    assert updated.json()["email"] == "new-admin@example.com"
    assert updated.json()["is_admin"] is True


def test_public_registration_cannot_claim_reserved_admin_name(client):
    response = register(client, username="SITEADMIN", email="attacker@example.com")
    assert response.status_code == 409


def test_existing_uppercase_username_is_not_admin(client):
    with TestingSessionLocal() as db:
        db.add(Member(username="SITEADMIN", email="uppercase@example.com", password_hash=members.hash_password("UpperPass123")))
        db.commit()
    login = client.post(
        "/api/v1/members/login",
        json={"identifier": "SITEADMIN", "password": "UpperPass123"},
    )
    assert login.status_code == 200
    assert login.json()["is_admin"] is False
    assert client.get("/api/v1/admin/overview").status_code == 403


def test_member_usage_starts_at_100_and_is_persistent(client):
    assert register(client).status_code == 201
    usage = client.get("/api/v1/ai/usage", params={"session_id": "session-12345"})
    assert usage.json() == {"authenticated": True, "limit": 100, "used": 0, "remaining": 100}

    chat = client.post(
        "/api/v1/ai/chat",
        headers=csrf_headers(client),
        json={"session_id": "session-12345", "message": "iPhone について教えて", "language": "ja"},
    )
    assert chat.status_code == 200
    assert chat.json()["remaining"] == 99
    assert client.get("/api/v1/ai/usage", params={"session_id": "another-session"}).json()["remaining"] == 99
    with TestingSessionLocal() as db:
        conversation = db.query(AIConversationLog).one()
        assert conversation.member_id is not None
        assert conversation.question == "iPhone について教えて"
        assert conversation.answer
        assert len(conversation.session_hash) == 64
        assert conversation.session_hash != "session-12345"


def test_member_usage_cannot_exceed_limit():
    with TestingSessionLocal() as db:
        member = Member(username="quota", email="quota@example.com", password_hash="unused")
        db.add(member)
        db.commit()
        db.refresh(member)
        for expected in range(99, -1, -1):
            assert members.consume_member_ai_usage(db, member.id) == expected
        with pytest.raises(HTTPException) as exc:
            members.consume_member_ai_usage(db, member.id)
        assert exc.value.status_code == 429


def test_guest_ai_history_records_ip(client):
    chat = client.post(
        "/api/v1/ai/chat",
        headers={"x-forwarded-for": "198.51.100.77", "user-agent": "NOVA guest test"},
        json={"session_id": "guest-session-12345", "message": "iPhoneの使い方", "language": "ja"},
    )
    assert chat.status_code == 200
    with TestingSessionLocal() as db:
        conversation = db.query(AIConversationLog).one()
        assert conversation.member_id is None
        assert conversation.ip_address == "198.51.100.77"
        assert conversation.user_agent == "NOVA guest test"
        assert conversation.question == "iPhoneの使い方"


def test_admin_can_read_collection_and_price_sources(client):
    with TestingSessionLocal() as db:
        db.add(Member(username="siteadmin", email="admin@example.com", password_hash=members.hash_password("AdminPass123")))
        product = Product(name="iPhone 17 Pro 256GB", model="iPhone 17 Pro", capacity="256")
        store = Store(name="公式テスト店")
        run = CollectionRun(source_type="official", source_name="公式テスト店", store_name="公式テスト店", status="success")
        db.add_all([product, store, run])
        db.flush()
        db.add(Price(product_id=product.id, store_id=store.id, price=200000))
        db.commit()
    assert client.post("/api/v1/members/login", json={"identifier": "siteadmin", "password": "AdminPass123"}).status_code == 200
    assert client.get("/api/v1/admin/collection-runs").json()["items"][0]["source_type"] == "official"
    unknown_price = client.get("/api/v1/admin/prices").json()["items"][0]
    assert unknown_price["price"] == 200000
    assert unknown_price["source_type"] == "unknown"
    assert client.get("/api/v1/admin/prices", params={"source_type": "sheet"}).json()["items"] == []
    assert client.get("/api/v1/admin/prices", params={"source_type": "unknown"}).json()["items"][0]["id"] == unknown_price["id"]


def test_admin_modules_group_prices_and_show_member_and_ai_history(client):
    with TestingSessionLocal() as db:
        admin_member = Member(
            username="siteadmin",
            email="admin@example.com",
            password_hash=members.hash_password("AdminPass123"),
        )
        normal_member = Member(
            username="buyer",
            email="buyer@example.com",
            password_hash=members.hash_password("BuyerPass123"),
        )
        product = Product(name="iPhone 17 Pro Max 256GB", model="iPhone 17 Pro Max", capacity="256GB")
        store = Store(name="比較テスト店", website_url="https://store.example.com")
        official_run = CollectionRun(source_type="official", source_name="公式", store_name=store.name, status="success")
        sheet_run = CollectionRun(source_type="sheet", source_name="表", store_name=store.name, status="success")
        db.add_all([admin_member, normal_member, product, store, official_run, sheet_run])
        db.flush()
        official_price = Price(product_id=product.id, store_id=store.id, price=218000)
        sheet_price = Price(product_id=product.id, store_id=store.id, price=211000)
        db.add_all([official_price, sheet_price])
        db.flush()
        db.add_all([
            PriceCollectionSource(
                price_id=official_price.id,
                run_id=official_run.id,
                source_type="official",
                source_url="https://store.example.com/official",
            ),
            PriceCollectionSource(
                price_id=sheet_price.id,
                run_id=sheet_run.id,
                source_type="sheet",
                source_url="https://sheet.example.com",
            ),
            OfficialStoreProduct(
                store_id=store.id,
                run_id=official_run.id,
                model="iPhone 17 Pro Max",
                capacity="256",
                product_name="iPhone 17 Pro Max 256GB シルバー",
                jan_code="4549995649284",
                price=218000,
                source_url="https://store.example.com/product/1",
                collected_at=datetime.now(timezone.utc),
            ),
            AIConversationLog(
                member_id=normal_member.id,
                session_hash="a" * 64,
                question="会員の質問",
                answer="会員への回答",
                language="ja",
                ip_address="198.51.100.10",
            ),
            AIConversationLog(
                member_id=None,
                session_hash="b" * 64,
                question="訪問者の質問",
                answer="訪問者への回答",
                language="ja",
                ip_address="198.51.100.20",
            ),
        ])
        db.commit()
        rebuild_standard_price_index(db)

    login = client.post(
        "/api/v1/members/login",
        headers={"x-forwarded-for": "203.0.113.9", "user-agent": "NOVA admin test"},
        json={"identifier": "admin@example.com", "password": "AdminPass123"},
    )
    assert login.status_code == 200

    member_list = client.get("/api/v1/admin/members")
    assert member_list.status_code == 200
    admin_record = next(item for item in member_list.json()["items"] if item["username"] == "siteadmin")
    assert admin_record["last_login_at"]
    assert admin_record["login_count"] == 1
    login_history = client.get(f"/api/v1/admin/members/{admin_record['id']}/logins").json()["items"]
    assert login_history[0]["event_type"] == "login"
    assert login_history[0]["ip_address"] == "203.0.113.9"

    store_list = client.get("/api/v1/admin/price-stores")
    assert store_list.status_code == 200
    store_record = next(item for item in store_list.json()["items"] if item["name"] == "比較テスト店")
    assert store_record["product_count"] == 1
    assert store_record["official_catalog_count"] == 1
    assert store_record["official_price_count"] == 1
    assert store_record["official_mapped_count"] == 1
    assert store_record["official_standard_variant_count"] == 1
    assert store_record["official_unmapped_count"] == 0
    assert store_record["sheet_price_count"] == 1
    assert store_record["latest_at"]

    store_detail = client.get(f"/api/v1/admin/price-stores/{store_record['id']}")
    assert store_detail.status_code == 200
    price_record = store_detail.json()["items"][0]
    assert store_detail.json()["official_price_count"] == 1
    assert store_detail.json()["sheet_price_count"] == 1
    assert price_record["official"]["price"] == 218000
    assert price_record["sheet"]["price"] == 211000
    assert price_record["official"]["updated_at"]
    assert price_record["sheet"]["updated_at"]
    official_catalog = client.get(
        f"/api/v1/admin/price-stores/{store_record['id']}/official-products"
    ).json()
    assert official_catalog["source_product_count"] == 1
    assert official_catalog["mapped_source_count"] == 1
    assert official_catalog["unmapped_source_count"] == 0
    assert official_catalog["standard_variant_count"] == 1
    official_catalog = official_catalog["items"]
    assert official_catalog[0]["product_name"] == "iPhone 17 Pro Max 256GB シルバー"
    assert official_catalog[0]["standard_product"] == "iPhone 17 Pro Max 256"
    assert official_catalog[0]["jan_code"] == "4549995649284"
    assert official_catalog[0]["price"] == 218000

    all_history = client.get("/api/v1/admin/ai-history").json()
    assert all_history["total"] == 2
    guest_history = client.get("/api/v1/admin/ai-history", params={"actor": "guest"}).json()
    assert guest_history["total"] == 1
    assert guest_history["items"][0]["username"] is None
    assert guest_history["items"][0]["ip_address"] == "198.51.100.20"
    member_history = client.get("/api/v1/admin/ai-history", params={"actor": "member"}).json()
    assert member_history["total"] == 1
    assert member_history["items"][0]["username"] == "buyer"
