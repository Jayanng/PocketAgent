"""Token lifecycle: generate, hash, verify proof, issue new tokens."""
from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from backend.services.wallet_signing import EVM_CHAINS, verify_wallet_signature

# Canonical reissue-message format: "pocketagent:reissue:<agent_id>:<unix_ts>"
# Used by the wallet-signature reissue flow. The server MUST verify every
# part, not just the timestamp window — otherwise a signature valid for
# agent A (one of the user's own agents) can be replayed against agent B
# when both share the same wallet.
_CANONICAL_PREFIX = "pocketagent"
_CANONICAL_ACTION = "reissue"
_CANONICAL_PART_COUNT = 4
_DEFAULT_MAX_AGE_SECONDS = 300


def verify_canonical_reissue_message(
    message: str,
    expected_agent_id: str,
    max_age_seconds: int = _DEFAULT_MAX_AGE_SECONDS,
) -> tuple[bool, str]:
    """Validate a wallet-signed reissue challenge is well-formed and fresh.

    Returns (ok, reason). On success, reason is the empty string.

    Checks (in order):
      1. Format is exactly `<prefix>:<action>:<agent_id>:<ts>` (4 parts).
      2. Prefix == "pocketagent".
      3. Action == "reissue".
      4. agent_id matches the path parameter (binds signature to action).
      5. Timestamp is within ±max_age_seconds of server clock.

    The agent_id check is the load-bearing one: without it, a wallet
    signature valid for one agent could be replayed against any other
    agent owned by the same wallet.
    """
    try:
        parts = message.split(":")
        if len(parts) != _CANONICAL_PART_COUNT:
            return False, "Malformed challenge message"
        if parts[0] != _CANONICAL_PREFIX:
            return False, "Invalid message prefix"
        if parts[1] != _CANONICAL_ACTION:
            return False, "Invalid message action"
        if parts[2] != expected_agent_id:
            return False, "Message agent_id does not match target agent"
        ts = int(parts[3])
    except (ValueError, IndexError):
        return False, "Malformed challenge message"
    if abs(int(time.time()) - ts) > max_age_seconds:
        return False, "Challenge expired; sign a fresh message"
    return True, ""


def generate_access_token() -> str:
    """Generate a cryptographically random opaque token."""
    return secrets.token_urlsafe(48)


def hash_access_token(token: str) -> str:
    """Hash a token for storage. SHA-256 hex."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _expected_address_for_chain(agent: dict[str, Any], chain: str) -> str | None:
    """Resolve which address on `agent` should match `chain` for proof.

    EVM chains share a single primary wallet_address field; all other
    protocol families must have an explicit entry in wallet_addresses[chain].
    Falling back to the EVM address for non-EVM chains would produce false
    positives (the EVM address is not a valid Solana base58 / Sui blake2b /
    NEAR hex / TRON base58check address), so we require an exact chain match.
    """
    addresses = agent.get("wallet_addresses") or {}
    if isinstance(addresses, dict):
        addr = addresses.get(chain)
        if addr:
            return str(addr)
    if chain in EVM_CHAINS and agent.get("wallet_address"):
        return str(agent["wallet_address"])
    return None


def verify_proof(agent: dict[str, Any], proof: dict[str, Any]) -> bool:
    """Verify a reissue proof against an agent. Returns True if valid.

    Two proof types supported:
      - current_token: caller knows the existing token
      - wallet_signature: caller signed the canonical message with the
        wallet that owns this agent (per-chain verification)
    """
    proof_type = proof.get("type")
    if proof_type == "current_token":
        submitted = proof.get("token", "")
        if not submitted:
            return False
        stored = agent.get("access_token_hash")
        if not stored:
            return False
        return hash_access_token(submitted) == stored
    if proof_type == "wallet_signature":
        chain = proof.get("chain", "")
        expected = _expected_address_for_chain(agent, chain)
        if not expected:
            return False
        return verify_wallet_signature(
            chain=chain,
            message=proof.get("message", ""),
            signature=proof.get("signature", ""),
            public_key=proof.get("public_key"),
            expected_address=expected,
        )
    return False


__all__ = [
    "generate_access_token",
    "hash_access_token",
    "verify_canonical_reissue_message",
    "verify_proof",
]
