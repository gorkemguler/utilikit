"""Shared fixtures. Env is set before any ``utilikit`` import."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="utilikit-test-"))
os.environ.setdefault("UTILIKIT_DATA_DIR", str(_TMP))
os.environ.setdefault("UTILIKIT_API_KEYS", "")
os.environ.setdefault("UTILIKIT_BROWSER_ENABLED", "false")
os.environ.setdefault("UTILIKIT_RATE_LIMIT_PER_MIN", "100000")
os.environ.setdefault("UTILIKIT_RATE_LIMIT_BURST", "100000")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    from utilikit.db import _local, init_db

    if hasattr(_local, "conn"):
        _local.conn.close()
        del _local.conn
    for f in _TMP.glob("utilikit.db*"):
        f.unlink()
    init_db()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from utilikit.app import create_app

    return TestClient(create_app())


@pytest.fixture
def keyed_client(monkeypatch):
    """A client where an API key IS required."""
    from fastapi.testclient import TestClient

    from utilikit import config

    monkeypatch.setenv("UTILIKIT_API_KEYS", "secret-key-1,secret-key-2")
    config.get_settings.cache_clear()
    from utilikit.app import create_app

    c = TestClient(create_app())
    yield c
    config.get_settings.cache_clear()
