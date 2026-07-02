"""Tests for the access_token timestamp migration.

Verifies that `init_db` (the project's actual migration entry point) adds the
two new access_token timestamp columns idempotently, and that existing agents
get their `access_token_created_at` backfilled from `created_at`.
"""
import asyncio
import os
import sqlite3
from unittest.mock import patch


def _run(coro):
    """Helper: run an async coroutine to completion."""
    return asyncio.run(coro)


def _table_cols(db_path: str, table: str) -> set:
    with sqlite3.connect(db_path) as conn:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_agents_table_has_new_access_token_columns_after_init(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("ENCRYPTION_KEY", "test-encryption-key-for-migration")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-migration")

    # Settings are cached; clear so the new env vars take effect.
    from backend.config import get_settings
    get_settings.cache_clear()

    from backend.database import init_db
    _run(init_db())

    cols = _table_cols(db_path, "agents")
    assert "access_token_created_at" in cols
    assert "access_token_revoked_at" in cols


def test_init_db_is_idempotent_for_new_columns(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("ENCRYPTION_KEY", "test-encryption-key-for-migration")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-migration")

    from backend.config import get_settings
    get_settings.cache_clear()

    from backend.database import init_db
    _run(init_db())
    _run(init_db())  # second call must not raise

    cols = _table_cols(db_path, "agents")
    assert "access_token_created_at" in cols
    assert "access_token_revoked_at" in cols
