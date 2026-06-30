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


def test_solana_valid_signature():
    fixture = json.loads((FIXTURES / "solana.json").read_text())
    assert verify_wallet_signature(
        chain="solana",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_solana_invalid_signature():
    fixture = json.loads((FIXTURES / "solana.json").read_text())
    assert not verify_wallet_signature(
        chain="solana",
        message=fixture["message"],
        signature="1" * 88,
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_solana_wrong_address():
    fixture = json.loads((FIXTURES / "solana.json").read_text())
    wrong = "11111111111111111111111111111112"
    assert not verify_wallet_signature(
        chain="solana",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=wrong,
        expected_address=fixture["address"],
    )


def test_sui_valid_signature():
    fixture = json.loads((FIXTURES / "sui.json").read_text())
    assert verify_wallet_signature(
        chain="sui",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_sui_invalid_signature():
    fixture = json.loads((FIXTURES / "sui.json").read_text())
    # base64 of 64 zero bytes
    import base64
    bad_sig = base64.b64encode(b"\x00" * 64).decode()
    assert not verify_wallet_signature(
        chain="sui",
        message=fixture["message"],
        signature=bad_sig,
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_sui_wrong_address():
    fixture = json.loads((FIXTURES / "sui.json").read_text())
    wrong = "0x" + "00" * 32
    assert not verify_wallet_signature(
        chain="sui",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=wrong,
    )
