"""Password hashing and the validation shared by member endpoints."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from fastapi import HTTPException


PASSWORD_ITERATIONS = 600_000
MAX_PASSWORD_ITERATIONS = 2_000_000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _parse_password_hash(password_hash: str | None) -> tuple[int, str, str] | None:
    if not password_hash or len(password_hash) > 512:
        return None
    try:
        algorithm, iterations_text, salt, digest = password_hash.split("$", 3)
        iterations = int(iterations_text)
        bytes.fromhex(digest)
    except ValueError:
        return None
    if (
        algorithm != "pbkdf2_sha256"
        or iterations < 1
        or iterations > MAX_PASSWORD_ITERATIONS
        or len(salt) < 16
        or len(digest) != 64
    ):
        return None
    return iterations, salt, digest


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
    parsed = _parse_password_hash(password_hash)
    if parsed is None:
        return False
    iterations, salt, expected_digest = parsed
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


def password_hash_needs_upgrade(password_hash: str | None) -> bool:
    parsed = _parse_password_hash(password_hash)
    return parsed is None or parsed[0] < PASSWORD_ITERATIONS


def normalize_password(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Password must be 8 to 128 characters")
    return password


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 255 or not EMAIL_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail="Email format is invalid")
    return normalized
