"""Token lifecycle: generate, hash, verify proof, issue new tokens."""
from __future__ import annotations

import hashlib
import secrets
from typing import Any

from backend.services.wallet_signing import EVM_CHAINS, verify_wallet_signature


def generate_access_token() -> str:
    """Generate a cryptographically random opaque token."""
    return secrets.token_urlsafe(48)


def hash_access_token(token: str) -> str:
    """Hash a token for storage. SHA-256 hex."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _expected_address_for_chain(agent: dict[str, Any], chain: str) -> str | None:
    """Resolve which address on `agent` should match `chain` for proof."""
    addresses = agent.get("wallet_addresses") or {}
    if isinstance(addresses, dict):
        addr = addresses.get(chain)
        if addr:
            return str(addr)
    if chain in EVM_CHAINS and agent.get("wallet_address"):
        return str(agent["wallet_address"])
    # Solana/Sui/NEAR/Cosmos/TRON may also live on the primary wallet_address
    if chain in ("solana", "near", "sui", "tron") and agent.get("wallet_address"):
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


__all__ = ["generate_access_token", "hash_access_token", "verify_proof"]
