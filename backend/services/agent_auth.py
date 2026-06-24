from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

try:
    from ..config import get_settings
except ImportError:
    from config import get_settings


def generate_agent_access_token() -> str:
    return secrets.token_urlsafe(32)


def hash_agent_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_agent_access_token(agent: dict[str, Any], token: str | None) -> bool:
    try:
        settings = get_settings()
        if getattr(settings, "disable_agent_auth", False):
            return True
    except Exception:
        pass

    expected_hash = agent.get("access_token_hash")
    if not expected_hash:
        return True  # Allow access to legacy/seeded agents that don't have a token hash
    if not token:
        return False
    supplied_hash = hash_agent_access_token(token)
    return hmac.compare_digest(str(expected_hash), supplied_hash)

