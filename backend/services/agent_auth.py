from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any


def generate_agent_access_token() -> str:
    return secrets.token_urlsafe(32)


def hash_agent_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_agent_access_token(agent: dict[str, Any], token: str | None) -> bool:
    expected_hash = agent.get("access_token_hash")
    if not expected_hash or not token:
        return False
    supplied_hash = hash_agent_access_token(token)
    return hmac.compare_digest(str(expected_hash), supplied_hash)
