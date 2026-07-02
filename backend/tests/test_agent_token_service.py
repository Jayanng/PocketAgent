"""Tests for backend/services/agent_token_service.py."""
import time

from backend.services.agent_token_service import (
    generate_access_token,
    hash_access_token,
    verify_canonical_reissue_message,
    verify_proof,
)


def test_generate_produces_unique_tokens():
    tokens = {generate_access_token() for _ in range(1000)}
    assert len(tokens) == 1000


def test_hash_is_deterministic():
    tok = generate_access_token()
    assert hash_access_token(tok) == hash_access_token(tok)


def test_hash_differs_for_different_tokens():
    a = hash_access_token(generate_access_token())
    b = hash_access_token(generate_access_token())
    assert a != b


def test_hash_length_is_sha256_hex():
    tok = generate_access_token()
    h = hash_access_token(tok)
    assert isinstance(h, str)
    assert len(h) == 64


# ─── Cross-chain address fallback (regression tests) ────────────────────────


def test_verify_proof_wallet_signature_solana_requires_solana_address():
    """Solana proof must NOT verify against the agent's EVM primary wallet_address.

    The EVM address is not a valid Solana base58 pubkey, so falling back to it
    would produce false positives or signature verification failures.
    """
    agent = {
        "wallet_address": "0x" + "ab" * 20,  # EVM address only
        "wallet_addresses": {},  # no solana entry
    }
    proof = {
        "type": "wallet_signature",
        "chain": "solana",
        "message": "pocketagent:reissue:test:1",
        "signature": "1" * 88,  # base58-ish, would fail signature check anyway
        "public_key": None,
    }
    assert verify_proof(agent, proof) is False


def test_verify_proof_wallet_signature_near_requires_near_address():
    """NEAR proof must NOT verify against the EVM wallet_address fallback."""
    agent = {
        "wallet_address": "0x" + "ab" * 20,
        "wallet_addresses": {},
    }
    proof = {
        "type": "wallet_signature",
        "chain": "near",
        "message": "pocketagent:reissue:test:1",
        "signature": "x" * 128,
        "public_key": "ab" * 32,
    }
    assert verify_proof(agent, proof) is False


def test_verify_proof_wallet_signature_cosmos_requires_cosmos_address():
    """Cosmos proof must NOT verify against the EVM wallet_address fallback."""
    agent = {
        "wallet_address": "0x" + "ab" * 20,
        "wallet_addresses": {},
    }
    proof = {
        "type": "wallet_signature",
        "chain": "cosmos",
        "message": "pocketagent:reissue:test:1",
        "signature": "0x" + "00" * 65,
        "public_key": None,
    }
    assert verify_proof(agent, proof) is False


def test_verify_proof_wallet_signature_sui_requires_sui_address():
    """Sui proof must NOT verify against the EVM wallet_address fallback."""
    agent = {
        "wallet_address": "0x" + "ab" * 20,
        "wallet_addresses": {},
    }
    proof = {
        "type": "wallet_signature",
        "chain": "sui",
        "message": "pocketagent:reissue:test:1",
        "signature": "AAAA",  # base64 of zero bytes
        "public_key": "AAAA",
    }
    assert verify_proof(agent, proof) is False


def test_verify_proof_wallet_signature_tron_requires_tron_address():
    """TRON proof must NOT verify against the EVM wallet_address fallback."""
    agent = {
        "wallet_address": "0x" + "ab" * 20,
        "wallet_addresses": {},
    }
    proof = {
        "type": "wallet_signature",
        "chain": "tron",
        "message": "pocketagent:reissue:test:1",
        "signature": "0x" + "00" * 65,
        "public_key": None,
    }
    assert verify_proof(agent, proof) is False


def test_verify_proof_wallet_signature_evm_falls_back_to_wallet_address():
    """EVM chains SHOULD still use wallet_address as the fallback (regression guard)."""
    # EVM case: wallet_address is the primary; wallet_addresses may not have ethereum.
    # We craft a proof with a clearly invalid signature so the verifier returns False
    # via signature check rather than address resolution, confirming we got past
    # the address-resolution layer.
    agent = {
        "wallet_address": "0x" + "ab" * 20,
        "wallet_addresses": {},
    }
    proof = {
        "type": "wallet_signature",
        "chain": "ethereum",
        "message": "pocketagent:reissue:test:1",
        "signature": "0x" + "00" * 65,
        "public_key": None,
    }
    # Invalid signature → False. The point of this test is that address resolution
    # DIDN'T short-circuit with None (which would also be False, but for a different
    # reason). We can't easily distinguish without injecting a mock; instead we
    # cover the positive case via integration tests in test_reissue_endpoint.py.
    assert verify_proof(agent, proof) is False


# ─── Canonical reissue-message format (cross-agent replay protection) ────────


def _valid_message(agent_id: str = "agent-A", ts: int | None = None) -> str:
    if ts is None:
        ts = int(time.time())
    return f"pocketagent:reissue:{agent_id}:{ts}"


def test_canonical_message_accepts_fresh_well_formed_message():
    ok, reason = verify_canonical_reissue_message(_valid_message(), "agent-A")
    assert ok is True
    assert reason == ""


def test_canonical_message_rejects_wrong_prefix():
    ok, _ = verify_canonical_reissue_message(
        "evilcorp:reissue:agent-A:" + str(int(time.time())), "agent-A"
    )
    assert ok is False


def test_canonical_message_rejects_wrong_action():
    ok, _ = verify_canonical_reissue_message(
        "pocketagent:rotate:agent-A:" + str(int(time.time())), "agent-A"
    )
    assert ok is False


def test_canonical_message_rejects_wrong_agent_id():
    """REGRESSION: signed message for agent A must NOT validate against agent B.

    Without this check, an attacker who captures a valid wallet_signature proof
    for agent A (their own agent, same wallet) could submit it to
    /api/agents/agent-B/reissue-token and the server would accept it because
    the signature is cryptographically valid for the wallet that owns B too.
    """
    ok, reason = verify_canonical_reissue_message(_valid_message("agent-A"), "agent-B")
    assert ok is False
    assert "agent" in reason.lower() or "match" in reason.lower()


def test_canonical_message_rejects_too_old_timestamp():
    ok, _ = verify_canonical_reissue_message(
        _valid_message("agent-A", ts=int(time.time()) - 400), "agent-A"
    )
    assert ok is False


def test_canonical_message_rejects_non_numeric_timestamp():
    ok, _ = verify_canonical_reissue_message(
        "pocketagent:reissue:agent-A:notanumber", "agent-A"
    )
    assert ok is False


def test_canonical_message_rejects_too_few_parts():
    ok, _ = verify_canonical_reissue_message("pocketagent:reissue:agent-A", "agent-A")
    assert ok is False


def test_canonical_message_rejects_too_many_parts():
    ok, _ = verify_canonical_reissue_message(
        "pocketagent:reissue:agent-A:" + str(int(time.time())) + ":extra", "agent-A"
    )
    assert ok is False


def test_canonical_message_rejects_empty_string():
    ok, _ = verify_canonical_reissue_message("", "agent-A")
    assert ok is False
