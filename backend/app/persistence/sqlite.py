import math
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from threading import RLock


class SQLiteDatabase:
    def __init__(self, path: str | Path = ":memory:", *, timeout: float = 5.0):
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("timeout must be finite and nonnegative")
        self._lock = RLock()
        self._closed = False
        self._connection = sqlite3.connect(
            str(path),
            timeout=timeout,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        with self._lock:
            if self._closed:
                raise RuntimeError("Database is closed")
            if self._connection.in_transaction:
                raise RuntimeError("Nested transactions are not supported")
            self._connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield self._connection
                self._connection.commit()
            except BaseException:
                self._connection.rollback()
                raise

    def initialize(self, statements: Sequence[str]) -> None:
        with self.transaction(immediate=True) as connection:
            for statement in statements:
                connection.execute(statement)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            if self._connection.in_transaction:
                raise RuntimeError("Cannot close an active transaction")
            self._connection.close()
            self._closed = True

    def __enter__(self) -> "SQLiteDatabase":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
