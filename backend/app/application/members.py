import hmac
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import replace
from uuid import uuid4

from app.config import MemberSettings
from app.contracts.members import MemberStore, MemberTransaction, RateLimiter
from app.domain.members import (
    ConcurrentUpdate,
    IdentityConflict,
    LoginResult,
    MemberError,
    MemberView,
    StoredMember,
    StoredSession,
)
from app.security.passwords import EMAIL_PATTERN, hash_password, verify_password
from app.security.tokens import token_hash


def _profile(username: str, email: str) -> tuple[str, str]:
    username = username.strip()
    email = email.strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username):
        raise MemberError("invalid_username")
    if len(email) > 255 or not EMAIL_PATTERN.fullmatch(email):
        raise MemberError("invalid_email")
    return username, email


def _password(password: str) -> str:
    if not 8 <= len(password) <= 128:
        raise MemberError("invalid_password")
    return password


class MemberService:
    def __init__(
        self,
        store: MemberStore,
        limiter: RateLimiter,
        settings: MemberSettings | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ):
        self.store = store
        self.limiter = limiter
        self.settings = settings or MemberSettings()
        self.clock = clock
        self._dummy_hash = hash_password(secrets.token_urlsafe(32))

    def _throttle(self, scope: str, client_key: str) -> None:
        if not client_key or len(client_key) > 256:
            raise MemberError("invalid_client_key")
        key = f"{scope}:client:{token_hash(client_key)}"
        if not self.limiter.allow(
            key, self.settings.attempts_per_client, self.settings.rate_window_seconds
        ):
            raise MemberError("rate_limited")

    def _account_throttle(self, scope: str, account: str) -> None:
        key = f"{scope}:account:{token_hash(account)}"
        if not self.limiter.allow(
            key, self.settings.attempts_per_account, self.settings.rate_window_seconds
        ):
            raise MemberError("rate_limited")

    def register(
        self, username: str, email: str, password: str, *, client_key: str
    ) -> MemberView:
        self._throttle("register", client_key)
        username, email = _profile(username, email)
        member = StoredMember(
            str(uuid4()), username, email, hash_password(_password(password))
        )
        try:
            with self.store.transaction() as tx:
                tx.insert_member(member)
        except IdentityConflict:
            raise MemberError("identity_unavailable") from None
        return member.view()

    def login(self, identity: str, password: str, *, client_key: str) -> LoginResult:
        identity = identity.strip().lower()
        if not identity or len(identity) > 255 or len(password) > 128:
            raise MemberError("invalid_credentials")
        self._throttle("login", client_key)
        with self.store.transaction() as tx:
            member = tx.find_identity(identity)
            self._account_throttle("login", member.id if member else identity)
            valid = verify_password(
                password, member.password_hash if member else self._dummy_hash
            )
            if not valid or member is None or not member.active:
                raise MemberError("invalid_credentials")
            now = int(self.clock())
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            session = StoredSession(
                token_hash(token),
                token_hash(csrf),
                member.id,
                now,
                now + self.settings.session_seconds,
            )
            tx.delete_expired_sessions(now)
            tx.insert_session(session, self.settings.max_sessions)
        return LoginResult(member.view(), token, csrf, session.expires_at)

    def _context(
        self, tx: MemberTransaction, token: str
    ) -> tuple[StoredMember, StoredSession]:
        if not token or len(token) > 128:
            raise MemberError("unauthorized")
        session = tx.get_session(token_hash(token))
        if session is None or session.expires_at <= int(self.clock()):
            raise MemberError("unauthorized")
        member = tx.get_member(session.member_id)
        if member is None or not member.active:
            raise MemberError("unauthorized")
        return member, session

    @staticmethod
    def _csrf(session: StoredSession, csrf: str) -> None:
        if (
            not csrf
            or len(csrf) > 128
            or not hmac.compare_digest(session.csrf_hash, token_hash(csrf))
        ):
            raise MemberError("csrf_failed")

    def current(self, token: str) -> MemberView:
        with self.store.transaction() as tx:
            member, _ = self._context(tx, token)
            return member.view()

    def logout(self, token: str, csrf: str) -> None:
        with self.store.transaction() as tx:
            _, session = self._context(tx, token)
            self._csrf(session, csrf)
            tx.delete_session(session.token_hash)

    def update_profile(
        self,
        token: str,
        csrf: str,
        password: str,
        *,
        username: str,
        email: str,
        client_key: str,
    ) -> MemberView:
        self._throttle("reauth", client_key)
        username, email = _profile(username, email)
        try:
            with self.store.transaction() as tx:
                member, session = self._context(tx, token)
                self._csrf(session, csrf)
                self._account_throttle("reauth", member.id)
                if len(password) > 128 or not verify_password(
                    password, member.password_hash
                ):
                    raise MemberError("invalid_credentials")
                tx.update_profile(member, username, email)
                if email != member.email:
                    tx.revoke_sessions(member.id, keep=session.token_hash)
        except IdentityConflict:
            raise MemberError("identity_unavailable") from None
        except ConcurrentUpdate:
            raise MemberError("retry_required") from None
        return replace(member, username=username, email=email).view()

    def change_password(
        self,
        token: str,
        csrf: str,
        current_password: str,
        new_password: str,
        *,
        client_key: str,
    ) -> None:
        self._throttle("reauth", client_key)
        _password(new_password)
        try:
            with self.store.transaction() as tx:
                member, session = self._context(tx, token)
                self._csrf(session, csrf)
                self._account_throttle("reauth", member.id)
                if len(current_password) > 128 or not verify_password(
                    current_password, member.password_hash
                ):
                    raise MemberError("invalid_credentials")
                tx.update_password(member, hash_password(new_password))
                tx.revoke_sessions(member.id)
        except ConcurrentUpdate:
            raise MemberError("retry_required") from None
