from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

import pytest
from app.application.members import MemberService
from app.config import MemberSettings
from app.domain.members import MemberError
from app.persistence.members import SQLiteMemberStore, SQLiteMemberTransaction
from app.persistence.sqlite import SQLiteDatabase
from app.security.local_rate_limit import SlidingWindowLimiter
from app.security.tokens import token_hash

PASSWORD = "sample-passphrase-42"


@pytest.fixture
def system():
    now = [1_800_000_000.0]
    with SQLiteDatabase() as database:
        store = SQLiteMemberStore(database)
        settings = MemberSettings(max_sessions=2)
        service = MemberService(
            store, SlidingWindowLimiter(), settings, clock=lambda: now[0]
        )
        yield service, database, now


def register(service, username="sample_user", email="sample@example.test"):
    return service.register(username, email, PASSWORD, client_key="test-client")


def login(service, identity="sample_user", password=PASSWORD):
    return service.login(identity, password, client_key="test-client")


def test_register_and_login_by_username_or_email(system):
    service, database, _ = system
    member = register(service, "Sample_User", " SAMPLE@EXAMPLE.TEST ")
    first = login(service, "sample_user")
    second = login(service, " SAMPLE@EXAMPLE.TEST ")
    assert first.member == second.member == member
    assert service.current(first.token) == member
    assert set(asdict(member)) == {"id", "username", "email"}
    assert first.token not in repr(first)
    with database.transaction() as connection:
        account = dict(connection.execute("SELECT * FROM accounts").fetchone())
        sessions = [dict(row) for row in connection.execute("SELECT * FROM sessions")]
    assert PASSWORD not in repr(account)
    assert first.token not in repr(sessions)
    assert first.csrf_token not in repr(sessions)
    assert any(row["token_hash"] == token_hash(first.token) for row in sessions)


@pytest.mark.parametrize(
    "username,email",
    [
        ("SAMPLE_USER", "other@example.test"),
        ("another_user", "SAMPLE@EXAMPLE.TEST"),
    ],
)
def test_duplicate_identity_is_rejected(system, username, email):
    service, _, _ = system
    register(service)
    with pytest.raises(MemberError, match="identity_unavailable"):
        register(service, username, email)


@pytest.mark.parametrize(
    "identity,password",
    [
        ("missing_user", PASSWORD),
        ("sample_user", "incorrect"),
        ("sample_user", "x" * 129),
        ("' OR 1=1 --", PASSWORD),
    ],
)
def test_failed_login_uses_same_error(system, identity, password):
    service, _, _ = system
    register(service)
    with pytest.raises(MemberError, match="invalid_credentials"):
        login(service, identity, password)


def test_session_expiry_at_exact_boundary(system):
    service, _, now = system
    register(service)
    session = login(service)
    now[0] = session.expires_at - 1
    assert service.current(session.token).username == "sample_user"
    now[0] += 1
    with pytest.raises(MemberError, match="unauthorized"):
        service.current(session.token)


def test_logout_requires_bound_csrf(system):
    service, _, _ = system
    register(service)
    first, second = login(service), login(service)
    with pytest.raises(MemberError, match="csrf_failed"):
        service.logout(first.token, second.csrf_token)
    assert service.current(first.token)
    service.logout(first.token, first.csrf_token)
    with pytest.raises(MemberError, match="unauthorized"):
        service.current(first.token)
    assert service.current(second.token)


def test_session_limit_keeps_newest_even_with_same_timestamp(system):
    service, _, _ = system
    register(service)
    first, second, third = login(service), login(service), login(service)
    with pytest.raises(MemberError, match="unauthorized"):
        service.current(first.token)
    assert service.current(second.token) == service.current(third.token)


def test_email_change_revokes_other_sessions(system):
    service, _, _ = system
    register(service)
    first, second = login(service), login(service)
    member = service.update_profile(
        first.token,
        first.csrf_token,
        PASSWORD,
        username="renamed_user",
        email="new@example.test",
        client_key="test-client",
    )
    assert service.current(first.token) == member
    assert login(service, "new@example.test").member == member
    with pytest.raises(MemberError, match="unauthorized"):
        service.current(second.token)
    with pytest.raises(MemberError, match="invalid_credentials"):
        login(service, "sample@example.test")


def test_profile_conflict_rolls_back(system):
    service, _, _ = system
    original = register(service)
    register(service, "second_user", "second@example.test")
    session = login(service)
    with pytest.raises(MemberError, match="identity_unavailable"):
        service.update_profile(
            session.token,
            session.csrf_token,
            PASSWORD,
            username="changed_user",
            email="second@example.test",
            client_key="test-client",
        )
    assert service.current(session.token) == original


@pytest.mark.parametrize(
    "csrf,password,error",
    [
        ("bad", PASSWORD, "csrf_failed"),
        (None, "incorrect", "invalid_credentials"),
    ],
)
def test_profile_change_requires_reauthentication(system, csrf, password, error):
    service, _, _ = system
    original = register(service)
    session = login(service)
    with pytest.raises(MemberError, match=error):
        service.update_profile(
            session.token,
            csrf or session.csrf_token,
            password,
            username="changed_user",
            email="changed@example.test",
            client_key="test-client",
        )
    assert service.current(session.token) == original


def test_password_change_revokes_every_session(system):
    service, _, _ = system
    register(service)
    first, second = login(service), login(service)
    service.change_password(
        first.token,
        first.csrf_token,
        PASSWORD,
        "new-sample-passphrase",
        client_key="test-client",
    )
    for session in (first, second):
        with pytest.raises(MemberError, match="unauthorized"):
            service.current(session.token)
    with pytest.raises(MemberError, match="invalid_credentials"):
        login(service)
    assert (
        login(service, password="new-sample-passphrase").member.username
        == "sample_user"
    )


def test_revocation_failure_rolls_back_password(system, monkeypatch):
    service, _, _ = system
    register(service)
    session = login(service)

    def fail(*args, **kwargs):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(SQLiteMemberTransaction, "revoke_sessions", fail)
    with pytest.raises(RuntimeError, match="storage unavailable"):
        service.change_password(
            session.token,
            session.csrf_token,
            PASSWORD,
            "new-sample-passphrase",
            client_key="test-client",
        )
    assert service.current(session.token)
    assert login(service).member == session.member


def test_disabled_member_cannot_login_or_use_existing_session(system):
    service, database, _ = system
    member = register(service)
    session = login(service)
    with database.transaction(immediate=True) as connection:
        connection.execute("UPDATE accounts SET active = 0 WHERE id = ?", (member.id,))
    with pytest.raises(MemberError, match="invalid_credentials"):
        login(service)
    with pytest.raises(MemberError, match="unauthorized"):
        service.current(session.token)


def test_account_throttle_applies_across_clients(system):
    service, _, _ = system
    for index in range(service.settings.attempts_per_account):
        with pytest.raises(MemberError, match="invalid_credentials"):
            service.login("absent", "incorrect", client_key=f"client-{index}")
    with pytest.raises(MemberError, match="rate_limited"):
        service.login("absent", "incorrect", client_key="new-client")


def test_concurrent_registration_has_one_winner(system):
    service, _, _ = system

    def attempt(index):
        try:
            return service.register(
                "same_user",
                f"user{index}@example.test",
                PASSWORD,
                client_key=str(index),
            )
        except MemberError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sum(result == "identity_unavailable" for result in results) == 1


@pytest.mark.parametrize(
    "username,email,password",
    [
        ("x", "sample@example.test", PASSWORD),
        ("contains@sign", "sample@example.test", PASSWORD),
        ("sample_user", "not-an-email", PASSWORD),
        ("sample_user", "sample@example.test", "short"),
    ],
)
def test_input_validation(system, username, email, password):
    service, _, _ = system
    with pytest.raises(MemberError):
        service.register(username, email, password, client_key="test-client")
