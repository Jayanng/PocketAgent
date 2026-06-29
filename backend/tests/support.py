"""Shared helpers for backend test fixtures."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import patch


AUTH_ENABLED_ENV = {
    "DISABLE_AGENT_AUTH": "false",
}


@contextmanager
def auth_enabled_settings() -> Iterator[None]:
    """Force agent auth on regardless of developer .env (matches production default)."""
    from backend.config import get_settings

    with patch.dict(os.environ, AUTH_ENABLED_ENV, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()