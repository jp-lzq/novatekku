import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Member, MemberAIUsage, MemberLoginEvent, MemberSession, PasswordResetToken
from app.web.schemas import (
    MemberChangePasswordRequest,
    MemberLoginRequest,
    MemberPasswordResetConfirm,
    MemberPasswordResetRequest,
    MemberProfileUpdateRequest,
    MemberRegisterRequest,
    MemberResponse,
    MessageResponse,
    PasswordResetAvailabilityResponse,
)
from app.web.services.auth_security import auth_rate_limiter
from app.web.services.member_auth_control import member_auth_enabled
from app.web.services.member_email import send_password_reset_email

router = APIRouter()

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_ITERATIONS = 600_000
SESSION_COOKIE = "nova_session"
CSRF_COOKIE = "nova_csrf"
MEMBER_AI_LIMIT = 100
GENERIC_LOGIN_ERROR = "Username/email or password is invalid"
GENERIC_RESET_MESSAGE = "If the account exists, password reset instructions will be sent"
MEMBER_AUTH_PAUSED_DETAIL = "Member login and registration are temporarily unavailable"
MEMBER_AUTH_PAUSED_HEADERS = {"Retry-After": "3600"}


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations_text, salt, expected_digest = password_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256" or iterations < 1:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(24))


def password_hash_needs_upgrade(password_hash: str | None) -> bool:
    if not password_hash:
        return True
    try:
        algorithm, iterations_text, _, _ = password_hash.split("$", 3)
        return algorithm != "pbkdf2_sha256" or int(iterations_text) < PASSWORD_ITERATIONS
    except ValueError:
        return True


def normalize_password(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Password must be 8 to 128 characters")
    return password


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 255 or not EMAIL_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail="Email format is invalid")
    return normalized


def normalize_username(username: str) -> str:
    normalized = username.strip()
    if len(normalized) < 2 or len(normalized) > 50:
        raise HTTPException(status_code=422, detail="Username must be 2 to 50 characters")
    if any(char.isspace() for char in normalized):
        raise HTTPException(status_code=422, detail="Username cannot contain spaces")
    return normalized


def normalize_member_payload(payload: MemberRegisterRequest) -> tuple[str, str, str]:
    username = normalize_username(payload.username)
    email = normalize_email(payload.email)
    password = normalize_password(payload.password)
    return username, email, password


def normalize_login_identifier(payload: MemberLoginRequest) -> str:
    identifier = (payload.identifier or payload.email or "").strip().lower()
    if len(identifier) < 2 or len(identifier) > 255 or any(char.isspace() for char in identifier):
        raise HTTPException(status_code=422, detail="Username or email format is invalid")
    return identifier


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_admin_member(member: Member) -> bool:
    return member.username == settings.admin_username


def ensure_ai_usage(db: Session, member_id: int) -> MemberAIUsage:
    usage = db.get(MemberAIUsage, member_id)
    if usage:
        return usage
    usage = MemberAIUsage(member_id=member_id, used_count=0)
    db.add(usage)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        usage = db.get(MemberAIUsage, member_id)
    if not usage:
        raise HTTPException(status_code=500, detail="Unable to initialize AI usage")
    return usage


def member_response(db: Session, member: Member) -> dict:
    usage = ensure_ai_usage(db, member.id)
    return {
        "id": member.id,
        "username": member.username,
        "email": member.email,
        "status": member.status,
        "created_at": member.created_at,
        "is_admin": is_admin_member(member),
        "ai_remaining": max(MEMBER_AI_LIMIT - usage.used_count, 0),
    }


def get_member_ai_usage(db: Session, member_id: int) -> tuple[int, int]:
    usage = ensure_ai_usage(db, member_id)
    used = min(max(int(usage.used_count or 0), 0), MEMBER_AI_LIMIT)
    return used, MEMBER_AI_LIMIT - used


def consume_member_ai_usage(db: Session, member_id: int) -> int:
    """Atomically consume one lifetime consultation and return the remaining count."""
    ensure_ai_usage(db, member_id)
    updated = db.query(MemberAIUsage).filter(
        MemberAIUsage.member_id == member_id,
        MemberAIUsage.used_count < MEMBER_AI_LIMIT,
    ).update(
        {
            MemberAIUsage.used_count: MemberAIUsage.used_count + 1,
            MemberAIUsage.updated_at: func.now(),
        },
        synchronize_session=False,
    )
    db.commit()
    if updated != 1:
        raise HTTPException(status_code=429, detail="Free member consultation limit reached")
    usage = db.get(MemberAIUsage, member_id)
    return max(MEMBER_AI_LIMIT - int(usage.used_count), 0)


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def enforce_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = {item.rstrip("/") for item in settings.auth_origins_list}
    if origin.rstrip("/") not in allowed:
        raise HTTPException(status_code=403, detail="Origin is not allowed")


def check_auth_rate(request: Request, scope: str, account: str, account_limit: int) -> None:
    auth_rate_limiter.check(f"{scope}:ip", client_ip(request), account_limit * 3)
    auth_rate_limiter.check(f"{scope}:account", account, account_limit)


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    max_age = settings.auth_session_days * 24 * 60 * 60
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=max_age,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite="lax",
    )


def clear_auth_cookies(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.delete_cookie(SESSION_COOKIE, path="/", secure=settings.auth_cookie_secure, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=settings.auth_cookie_secure, httponly=False, samesite="lax")


def create_member_session(
    db: Session,
    member: Member,
    response: Response,
    request: Request,
    *,
    event_type: str,
) -> None:
    now = utc_now()
    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    db.query(MemberSession).filter(
        MemberSession.member_id == member.id,
        MemberSession.expires_at <= now,
    ).delete(synchronize_session=False)
    active_sessions = db.query(MemberSession).filter(
        MemberSession.member_id == member.id,
        MemberSession.revoked_at.is_(None),
    ).order_by(MemberSession.created_at.desc()).all()
    for old_session in active_sessions[9:]:
        old_session.revoked_at = now
    db.add(MemberSession(
        member_id=member.id,
        token_hash=token_hash(session_token),
        csrf_hash=token_hash(csrf_token),
        expires_at=now + timedelta(days=settings.auth_session_days),
    ))
    db.add(MemberLoginEvent(
        member_id=member.id,
        event_type=event_type,
        ip_address=client_ip(request)[:64],
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
    ))
    db.commit()
    set_auth_cookies(response, session_token, csrf_token)


@dataclass
class AuthContext:
    member: Member
    session: MemberSession


def get_optional_auth_context(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> AuthContext | None:
    if not session_token:
        return None
    session = db.query(MemberSession).filter(
        MemberSession.token_hash == token_hash(session_token),
        MemberSession.revoked_at.is_(None),
        MemberSession.expires_at > utc_now(),
    ).first()
    if not session or not session.member or session.member.status != "active":
        return None
    return AuthContext(member=session.member, session=session)


def get_auth_context(context: AuthContext | None = Depends(get_optional_auth_context)) -> AuthContext:
    if not context:
        raise HTTPException(status_code=401, detail="Authentication required")
    return context


def require_admin(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not is_admin_member(context.member):
        raise HTTPException(status_code=403, detail="Administrator access required")
    return context


def require_csrf(context: AuthContext, csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if not hmac.compare_digest(context.session.csrf_hash, token_hash(csrf_header)):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


@router.get("/members/auth-status")
def get_member_auth_status(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return {"enabled": member_auth_enabled(db)}


@router.post("/members/register", response_model=MemberResponse, status_code=201)
def register_member(payload: MemberRegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_trusted_origin(request)
    if not member_auth_enabled(db):
        raise HTTPException(
            status_code=503,
            detail=MEMBER_AUTH_PAUSED_DETAIL,
            headers=MEMBER_AUTH_PAUSED_HEADERS,
        )
    username, email, password = normalize_member_payload(payload)
    if username.lower() == settings.admin_username:
        raise HTTPException(status_code=409, detail="Username already registered")
    check_auth_rate(request, "register", email, 5)
    new_password_hash = hash_password(password)
    existing_member = db.query(Member).filter(
        (func.lower(Member.username) == username.lower()) | (Member.email == email)
    ).first()
    if existing_member:
        raise HTTPException(status_code=409, detail="Member already registered")
    member = Member(username=username, email=email, password_hash=new_password_hash)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member already registered")
    db.refresh(member)
    create_member_session(db, member, response, request, event_type="register")
    return member_response(db, member)


@router.post("/members/login", response_model=MemberResponse)
def login_member(payload: MemberLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_trusted_origin(request)
    identifier = normalize_login_identifier(payload)
    password = normalize_password(payload.password)
    check_auth_rate(request, "login", identifier, 10)
    member = db.query(Member).filter(
        (func.lower(Member.username) == identifier) | (func.lower(Member.email) == identifier)
    ).first()
    password_hash = member.password_hash if member else DUMMY_PASSWORD_HASH
    password_valid = verify_password(password, password_hash)
    if not member or member.status != "active" or not password_valid:
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)
    if not member_auth_enabled(db) and not is_admin_member(member):
        raise HTTPException(
            status_code=503,
            detail=MEMBER_AUTH_PAUSED_DETAIL,
            headers=MEMBER_AUTH_PAUSED_HEADERS,
        )
    # Existing administrator credentials are deliberately left byte-for-byte unchanged.
    if not is_admin_member(member) and password_hash_needs_upgrade(member.password_hash):
        member.password_hash = hash_password(password)
        db.commit()
    create_member_session(db, member, response, request, event_type="login")
    return member_response(db, member)


@router.get("/members/me", response_model=MemberResponse)
def get_current_member(response: Response, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return member_response(db, context.member)


@router.post("/members/logout", response_model=MessageResponse)
def logout_member(
    request: Request,
    response: Response,
    context: AuthContext = Depends(get_auth_context),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-NOVA-CSRF"),
    db: Session = Depends(get_db),
):
    enforce_trusted_origin(request)
    require_csrf(context, csrf_cookie, csrf_header)
    context.session.revoked_at = utc_now()
    db.commit()
    clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.post("/members/profile", response_model=MemberResponse)
def update_member_profile(
    payload: MemberProfileUpdateRequest,
    request: Request,
    response: Response,
    context: AuthContext = Depends(get_auth_context),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-NOVA-CSRF"),
    db: Session = Depends(get_db),
):
    enforce_trusted_origin(request)
    require_csrf(context, csrf_cookie, csrf_header)
    check_auth_rate(request, "profile-update", str(context.member.id), 10)

    username = normalize_username(payload.username)
    email = normalize_email(payload.email)
    current_password = normalize_password(payload.current_password)
    if not verify_password(current_password, context.member.password_hash):
        raise HTTPException(status_code=401, detail="Current password is invalid")

    if is_admin_member(context.member) and username != settings.admin_username:
        raise HTTPException(status_code=422, detail="Administrator username cannot be changed")
    if not is_admin_member(context.member) and username.lower() == settings.admin_username:
        raise HTTPException(status_code=409, detail="Username is already in use")

    username_owner = db.query(Member).filter(
        Member.id != context.member.id,
        func.lower(Member.username) == username.lower(),
    ).first()
    if username_owner:
        raise HTTPException(status_code=409, detail="Username is already in use")

    email_owner = db.query(Member).filter(
        Member.id != context.member.id,
        func.lower(Member.email) == email,
    ).first()
    if email_owner:
        raise HTTPException(status_code=409, detail="Email is already in use")

    email_changed = context.member.email.lower() != email
    context.member.username = username
    context.member.email = email

    if email_changed:
        now = utc_now()
        db.query(MemberSession).filter(
            MemberSession.member_id == context.member.id,
            MemberSession.id != context.session.id,
            MemberSession.revoked_at.is_(None),
        ).update({MemberSession.revoked_at: now}, synchronize_session=False)
        db.query(PasswordResetToken).filter(
            PasswordResetToken.member_id == context.member.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email is already in use")

    db.refresh(context.member)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return member_response(db, context.member)


@router.post("/members/change-password", response_model=MessageResponse)
def change_member_password(
    payload: MemberChangePasswordRequest,
    request: Request,
    response: Response,
    context: AuthContext = Depends(get_auth_context),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-NOVA-CSRF"),
    db: Session = Depends(get_db),
):
    enforce_trusted_origin(request)
    require_csrf(context, csrf_cookie, csrf_header)
    check_auth_rate(request, "change-password", str(context.member.id), 5)
    current_password = normalize_password(payload.current_password)
    new_password = normalize_password(payload.new_password)
    if not verify_password(current_password, context.member.password_hash):
        raise HTTPException(status_code=401, detail="Current password is invalid")
    context.member.password_hash = hash_password(new_password)
    now = utc_now()
    db.query(MemberSession).filter(
        MemberSession.member_id == context.member.id,
        MemberSession.revoked_at.is_(None),
    ).update({MemberSession.revoked_at: now}, synchronize_session=False)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.member_id == context.member.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    clear_auth_cookies(response)
    return {"message": "Password changed; sign in again"}


@router.get("/members/password-reset/config", response_model=PasswordResetAvailabilityResponse)
def password_reset_config():
    return {"enabled": settings.password_reset_delivery_ready}


@router.post("/members/password-reset/request", response_model=MessageResponse, status_code=202)
def request_password_reset(
    payload: MemberPasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    enforce_trusted_origin(request)
    email = normalize_email(payload.email)
    check_auth_rate(request, "password-reset-request", email, 5)
    if not settings.password_reset_delivery_ready:
        return {"message": GENERIC_RESET_MESSAGE}
    raw_token = secrets.token_urlsafe(32)
    member = db.query(Member).filter(Member.email == email, Member.status == "active").first()
    if member:
        now = utc_now()
        db.query(PasswordResetToken).filter(
            PasswordResetToken.member_id == member.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        db.add(PasswordResetToken(
            member_id=member.id,
            token_hash=token_hash(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_token_minutes),
        ))
    db.commit()
    if member:
        background_tasks.add_task(send_password_reset_email, member.email, raw_token)
    return {"message": GENERIC_RESET_MESSAGE}


@router.post("/members/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(payload: MemberPasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    enforce_trusted_origin(request)
    check_auth_rate(request, "password-reset-confirm", client_ip(request), 10)
    password = normalize_password(payload.password)
    if len(payload.token) < 32 or len(payload.token) > 256:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash(payload.token),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > utc_now(),
    ).first()
    if not reset_token or not reset_token.member or reset_token.member.status != "active":
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    now = utc_now()
    reset_token.member.password_hash = hash_password(password)
    reset_token.used_at = now
    db.query(MemberSession).filter(
        MemberSession.member_id == reset_token.member_id,
        MemberSession.revoked_at.is_(None),
    ).update({MemberSession.revoked_at: now}, synchronize_session=False)
    db.commit()
    return {"message": "Password updated; sign in again"}


@router.post("/members/reset-password", status_code=410)
def deprecated_reset_password():
    raise HTTPException(status_code=410, detail="Use the verified password reset flow")
