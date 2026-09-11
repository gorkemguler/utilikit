"""Minimal SQLite helper for the two stateful tools (request bin, URL shortener).

Everything else in Utilikit is stateless. Kept to raw ``sqlite3`` so the app has
no ORM dependency.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from .config import get_settings

_local = threading.local()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shortlinks (
    code       TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    hits       INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bin_requests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    bin_id     TEXT NOT NULL,
    ts         TEXT NOT NULL DEFAULT (datetime('now')),
    method     TEXT NOT NULL,
    path       TEXT NOT NULL,
    query      TEXT NOT NULL DEFAULT '',
    headers    TEXT NOT NULL DEFAULT '{}',
    body       TEXT NOT NULL DEFAULT '',
    remote     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_bin_requests_bin ON bin_requests(bin_id, id DESC);
"""


def _conn() -> sqlite3.Connection:
    c = getattr(_local, "conn", None)
    if c is None:
        path = get_settings().db_path
        c = sqlite3.connect(path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=4000")
        _local.conn = c
    return c


def init_db() -> None:
    _conn().executescript(_SCHEMA)
    _conn().commit()


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    c = _conn()
    cur = c.cursor()
    try:
        yield cur
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        cur.close()
