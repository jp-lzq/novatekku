import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.domain.members import (
    ConcurrentUpdate,
    IdentityConflict,
    StoredMember,
    StoredSession,
)
from app.persistence.sqlite import SQLiteDatabase

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        username_key TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        revision INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        csrf_hash TEXT NOT NULL,
        member_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL CHECK (expires_at > created_at)
    )""",
    "CREATE INDEX IF NOT EXISTS sessions_member ON sessions(member_id, created_at)",
    "CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)",
)


def _member(row: sqlite3.Row | None) -> StoredMember | None:
    if row is None:
        return None
    return StoredMember(
        row["id"],
        row["username"],
        row["email"],
        row["password_hash"],
        row["revision"],
        bool(row["active"]),
    )


def _identity_error(error: sqlite3.IntegrityError) -> None:
    if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
        raise IdentityConflict from None
    raise error


class SQLiteMemberTransaction:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def find_identity(self, identity: str) -> StoredMember | None:
        return _member(
            self.connection.execute(
                "SELECT * FROM accounts WHERE username_key = ? OR email = ?",
                (identity, identity),
            ).fetchone()
        )

    def get_member(self, member_id: str) -> StoredMember | None:
        return _member(
            self.connection.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (member_id,),
            ).fetchone()
        )

    def insert_member(self, member: StoredMember) -> None:
        try:
            self.connection.execute(
                """INSERT INTO accounts
                (id, username, username_key, email, password_hash, revision, active)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    member.id,
                    member.username,
                    member.username.lower(),
                    member.email,
                    member.password_hash,
                    member.revision,
                    int(member.active),
                ),
            )
        except sqlite3.IntegrityError as error:
            _identity_error(error)

    def update_profile(self, member: StoredMember, username: str, email: str) -> None:
        try:
            result = self.connection.execute(
                """UPDATE accounts SET username = ?, username_key = ?, email = ?, revision = revision + 1
                WHERE id = ? AND revision = ?""",
                (username, username.lower(), email, member.id, member.revision),
            )
        except sqlite3.IntegrityError as error:
            _identity_error(error)
            return
        if result.rowcount != 1:
            raise ConcurrentUpdate

    def update_password(self, member: StoredMember, password_hash: str) -> None:
        result = self.connection.execute(
            "UPDATE accounts SET password_hash = ?, revision = revision + 1 WHERE id = ? AND revision = ?",
            (password_hash, member.id, member.revision),
        )
        if result.rowcount != 1:
            raise ConcurrentUpdate

    def get_session(self, token_hash: str) -> StoredSession | None:
        row = self.connection.execute(
            "SELECT * FROM sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        return StoredSession(**dict(row)) if row is not None else None

    def insert_session(self, session: StoredSession, limit: int) -> None:
        self.connection.execute(
            "INSERT INTO sessions (token_hash, csrf_hash, member_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (
                session.token_hash,
                session.csrf_hash,
                session.member_id,
                session.created_at,
                session.expires_at,
            ),
        )
        self.connection.execute(
            """DELETE FROM sessions WHERE token_hash IN (
                SELECT token_hash FROM sessions WHERE member_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET ?
            )""",
            (session.member_id, limit),
        )

    def delete_session(self, token_hash: str) -> None:
        self.connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?", (token_hash,)
        )

    def revoke_sessions(self, member_id: str, keep: str | None = None) -> None:
        if keep is None:
            self.connection.execute(
                "DELETE FROM sessions WHERE member_id = ?", (member_id,)
            )
        else:
            self.connection.execute(
                "DELETE FROM sessions WHERE member_id = ? AND token_hash <> ?",
                (member_id, keep),
            )

    def delete_expired_sessions(self, now: int) -> None:
        self.connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))


class SQLiteMemberStore:
    def __init__(self, database: SQLiteDatabase):
        self.database = database
        database.initialize(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[SQLiteMemberTransaction]:
        with self.database.transaction(immediate=True) as connection:
            yield SQLiteMemberTransaction(connection)
