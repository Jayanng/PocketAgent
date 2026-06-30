"""Tests for per-chain wallet signature verification (Phase 1 of token UX overhaul)."""
import json
from pathlib import Path

from backend.services.wallet_signing import verify_wallet_signature

FIXTURES = Path(__file__).parent / "fixtures" / "wallet_signing"


def test_evm_valid_signature():
    fixture = json.loads((FIXTURES / "evm.json").read_text())
    assert verify_wallet_signature(
        chain="ethereum",
        message=fixture["message"],
        signature="0x" + fixture["signature"],
        public_key=None,
        expected_address=fixture["address"],
    )


def test_evm_invalid_signature():
    fixture = json.loads((FIXTURES / "evm.json").read_text())
    bad_sig = "0x" + "00" * 65
    assert not verify_wallet_signature(
        chain="ethereum",
        message=fixture["message"],
        signature=bad_sig,
        public_key=None,
        expected_address=fixture["address"],
    )


def test_evm_wrong_address():
    fixture = json.loads((FIXTURES / "evm.json").read_text())
    assert not verify_wallet_signature(
        chain="ethereum",
        message=fixture["message"],
        signature="0x" + fixture["signature"],
        public_key=None,
        expected_address="0x0000000000000000000000000000000000000000",
    )
