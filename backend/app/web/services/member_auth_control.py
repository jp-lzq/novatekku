from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Member, MemberAuthControl

CONTROL_ROW_ID = 1


def member_auth_enabled(db: Session) -> bool:
    control = db.get(MemberAuthControl, CONTROL_ROW_ID)
    if control is None:
        return settings.public_member_auth_enabled
    return bool(control.enabled)


def member_auth_control_payload(db: Session) -> dict:
    control = db.get(MemberAuthControl, CONTROL_ROW_ID)
    if control is None:
        return {
            "enabled": settings.public_member_auth_enabled,
            "updated_at": None,
            "updated_by": None,
        }

    updated_by = db.get(Member, control.updated_by_member_id) if control.updated_by_member_id else None
    return {
        "enabled": bool(control.enabled),
        "updated_at": control.updated_at,
        "updated_by": updated_by.username if updated_by else None,
    }


def set_member_auth_enabled(db: Session, enabled: bool, updated_by_member_id: int | None) -> dict:
    control = db.get(MemberAuthControl, CONTROL_ROW_ID)
    if control is None:
        control = MemberAuthControl(
            id=CONTROL_ROW_ID,
            enabled=enabled,
            updated_by_member_id=updated_by_member_id,
        )
        db.add(control)
    else:
        control.enabled = enabled
        control.updated_by_member_id = updated_by_member_id
    db.commit()
    db.refresh(control)
    return member_auth_control_payload(db)
