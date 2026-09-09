import sqlite3

import pytest
from app.domain.members import ConcurrentUpdate, StoredMember
from app.persistence.members import SQLiteMemberStore
from app.persistence.sqlite import SQLiteDatabase


def test_transaction_rollback_and_reopen(tmp_path):
    path = tmp_path / "sample.sqlite"
    with SQLiteDatabase(path) as database:
        database.initialize(["CREATE TABLE sample (value TEXT NOT NULL)"])
        with database.transaction() as connection:
            connection.execute("INSERT INTO sample VALUES (?)", ("committed",))
        with pytest.raises(RuntimeError):
            with database.transaction() as connection:
                connection.execute("INSERT INTO sample VALUES (?)", ("rolled back",))
                raise RuntimeError("failure")
    with SQLiteDatabase(path) as reopened:
        with reopened.transaction() as connection:
            assert [
                row[0] for row in connection.execute("SELECT value FROM sample")
            ] == ["committed"]


def test_interrupt_rolls_back():
    with SQLiteDatabase() as database:
        database.initialize(["CREATE TABLE sample (value INTEGER)"])
        with pytest.raises(KeyboardInterrupt):
            with database.transaction() as connection:
                connection.execute("INSERT INTO sample VALUES (1)")
                raise KeyboardInterrupt
        with database.transaction() as connection:
            assert connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 0


def test_nested_transaction_does_not_commit_outer_transaction():
    with SQLiteDatabase() as database:
        database.initialize(["CREATE TABLE sample (value INTEGER)"])
        with pytest.raises(RuntimeError, match="Nested"):
            with database.transaction() as connection:
                connection.execute("INSERT INTO sample VALUES (1)")
                with database.transaction():
                    pass
        with database.transaction() as connection:
            assert connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 0


def test_schema_initialization_is_atomic():
    with SQLiteDatabase() as database:
        with pytest.raises(sqlite3.OperationalError):
            database.initialize(["CREATE TABLE example (value TEXT)", "INVALID SQL"])
        with database.transaction() as connection:
            assert (
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'example'"
                ).fetchone()
                is None
            )


def test_stale_profile_write_rejected_across_connections(tmp_path):
    path = tmp_path / "sample.sqlite"
    with SQLiteDatabase(path) as first, SQLiteDatabase(path) as second:
        left, right = SQLiteMemberStore(first), SQLiteMemberStore(second)
        member = StoredMember(
            "sample-id", "sample_user", "sample@example.test", "unused"
        )
        with left.transaction() as tx:
            tx.insert_member(member)
        with right.transaction() as tx:
            tx.update_profile(member, "updated_user", member.email)
        with pytest.raises(ConcurrentUpdate):
            with left.transaction() as tx:
                tx.update_profile(member, "stale_user", member.email)
        with left.transaction() as tx:
            assert tx.get_member(member.id).username == "updated_user"


def test_close_is_idempotent_but_not_allowed_inside_transaction():
    database = SQLiteDatabase()
    with database.transaction():
        with pytest.raises(RuntimeError, match="active transaction"):
            database.close()
    database.close()
    database.close()
    with pytest.raises(RuntimeError, match="closed"):
        with database.transaction():
            pass
