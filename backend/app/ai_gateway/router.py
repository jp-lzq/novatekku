"""NOVA AI HTTP endpoints: usage limits, session history and conversation logs."""
import hashlib
import logging

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.ai_gateway import core as ai_core
from app.ai_gateway.preprocess import prepare_request
from app.ai_gateway.session import AI_HISTORY_MAX_MESSAGES, AI_SESSION_MAX, get_session_state
from app.db.models import AIConversationLog
from app.db.session import get_db
from app.web.routers.members import (
    CSRF_COOKIE,
    AuthContext,
    MEMBER_AI_LIMIT,
    consume_member_ai_usage,
    enforce_trusted_origin,
    get_member_ai_usage,
    get_optional_auth_context,
    client_ip,
    require_csrf,
)
from app.web.schemas import AIChatResponse, AIChatRequest, AIUsageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/ai/usage", response_model=AIUsageResponse)
def ai_usage(
    session_id: str = Query(min_length=8, max_length=128),
    context: AuthContext | None = Depends(get_optional_auth_context),
    db: Session = Depends(get_db),
):
    if context:
        used, remaining = get_member_ai_usage(db, context.member.id)
        return {
            "authenticated": True,
            "limit": MEMBER_AI_LIMIT,
            "used": used,
            "remaining": remaining,
        }
    state = get_session_state(session_id)
    used = min(int(state.get("count", 0)), AI_SESSION_MAX)
    return {
        "authenticated": False,
        "limit": AI_SESSION_MAX,
        "used": used,
        "remaining": AI_SESSION_MAX - used,
    }


@router.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(
    payload: AIChatRequest,
    request: Request,
    context: AuthContext | None = Depends(get_optional_auth_context),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-NOVA-CSRF"),
    db: Session = Depends(get_db),
):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    session_state = get_session_state(payload.session_id)
    if context:
        enforce_trusted_origin(request)
        require_csrf(context, csrf_cookie, csrf_header)
        _, member_remaining = get_member_ai_usage(db, context.member.id)
        if member_remaining <= 0:
            raise HTTPException(status_code=429, detail="Free member consultation limit reached")
    elif session_state["count"] >= AI_SESSION_MAX:
        raise HTTPException(status_code=429, detail="Daily limit reached")

    conversation_history = session_state.get("history", [])
    message = payload.message.strip()
    ai_request = prepare_request(db, message, payload.language, conversation_history)
    reply = ai_core.answer(ai_request)
    response_language = ai_request.language

    session_state["history"] = (
        conversation_history
        + [{"role": "user", "content": message}]
        + [{"role": "assistant", "content": reply}]
    )[-AI_HISTORY_MAX_MESSAGES:]
    if context:
        remaining = consume_member_ai_usage(db, context.member.id)
    else:
        session_state["count"] += 1
        remaining = max(AI_SESSION_MAX - session_state["count"], 0)

    try:
        db.add(AIConversationLog(
            member_id=context.member.id if context else None,
            session_hash=hashlib.sha256(payload.session_id.encode("utf-8")).hexdigest(),
            question=message,
            answer=reply,
            language=response_language,
            ip_address=client_ip(request)[:64],
            user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to save AI conversation history")

    return AIChatResponse(reply=reply, remaining=remaining)
