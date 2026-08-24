import hashlib
from datetime import datetime, timezone


def token_hash(token: str) -> str:
    # Tokens are generated with secrets.token_urlsafe before reaching here.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
