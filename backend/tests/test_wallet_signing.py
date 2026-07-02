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


def test_near_valid_signature():
    fixture = json.loads((FIXTURES / "near.json").read_text())
    assert verify_wallet_signature(
        chain="near",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_near_invalid_signature():
    fixture = json.loads((FIXTURES / "near.json").read_text())
    import base64
    bad_sig = base64.b64encode(b"\x00" * 64).decode()
    assert not verify_wallet_signature(
        chain="near",
        message=fixture["message"],
        signature=bad_sig,
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_near_wrong_address():
    fixture = json.loads((FIXTURES / "near.json").read_text())
    wrong = "ab" * 32
    assert not verify_wallet_signature(
        chain="near",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=wrong,
    )


def test_cosmos_valid_signature():
    fixture = json.loads((FIXTURES / "cosmos.json").read_text())
    assert verify_wallet_signature(
        chain="cosmos",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_cosmos_invalid_signature():
    fixture = json.loads((FIXTURES / "cosmos.json").read_text())
    bad_sig = "0x" + "00" * 65
    assert not verify_wallet_signature(
        chain="cosmos",
        message=fixture["message"],
        signature=bad_sig,
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_cosmos_wrong_address():
    fixture = json.loads((FIXTURES / "cosmos.json").read_text())
    wrong = "cosmos1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqg"
    assert not verify_wallet_signature(
        chain="cosmos",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=wrong,
    )


def test_tron_valid_signature():
    fixture = json.loads((FIXTURES / "tron.json").read_text())
    assert verify_wallet_signature(
        chain="tron",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_tron_invalid_signature():
    fixture = json.loads((FIXTURES / "tron.json").read_text())
    bad_sig = "0x" + "00" * 65
    assert not verify_wallet_signature(
        chain="tron",
        message=fixture["message"],
        signature=bad_sig,
        public_key=fixture["public_key"],
        expected_address=fixture["address"],
    )


def test_tron_wrong_address():
    fixture = json.loads((FIXTURES / "tron.json").read_text())
    wrong = "T" + "9" * 33
    assert not verify_wallet_signature(
        chain="tron",
        message=fixture["message"],
        signature=fixture["signature"],
        public_key=fixture["public_key"],
        expected_address=wrong,
    )


def test_cosmos_accepts_64byte_signature():
    """Real Cosmos wallets (Keplr etc.) emit 64-byte compact signatures per
    ADR-036, without the recovery byte. Stripping the recovery byte from our
    65-byte fixture must still verify.
    """
    fixture = json.loads((FIXTURES / "cosmos.json").read_text())
    sig_64 = "0x" + fixture["signature"][2:-2]  # drop trailing recovery byte
    assert len(sig_64) - 2 == 128
    assert verify_wallet_signature(
        chain="cosmos",
        message=fixture["message"],
        signature=sig_64,
        public_key=None,
        expected_address=fixture["address"],
    )


def test_tron_accepts_64byte_signature():
    """TRON wallets emit 64-byte compact signatures; verifier must accept them."""
    fixture = json.loads((FIXTURES / "tron.json").read_text())
    sig_64 = "0x" + fixture["signature"][2:-2]
    assert len(sig_64) - 2 == 128
    assert verify_wallet_signature(
        chain="tron",
        message=fixture["message"],
        signature=sig_64,
        public_key=None,
        expected_address=fixture["address"],
    )


def test_cosmos_osmosis_chain_uses_osmosis_hrp():
    """An address generated with the osmosis HRP must verify when chain='osmosis'."""
    import hashlib
    import bech32 as _bech32
    from coincurve import PrivateKey
    from Crypto.Hash import RIPEMD160

    priv_bytes = hashlib.sha256(b"osmosis-test-key").digest()
    priv = PrivateKey(priv_bytes)
    message = "pocketagent:reissue:test-agent:1740000000"
    msg_bytes = message.encode("utf-8")
    prefix = b"\x19\x00" + len(msg_bytes).to_bytes(4, "big") + hashlib.sha256(msg_bytes).digest()
    to_sign = hashlib.sha256(prefix).digest()
    sig = priv.sign_recoverable(to_sign, hasher=None)
    # Recover pubkey and derive osmosis address
    from coincurve import PublicKey
    vk = PublicKey.from_signature_and_message(sig, to_sign, hasher=None)
    uncompressed = vk.format(compressed=False)
    sha = hashlib.sha256(uncompressed[1:]).digest()
    ripe = RIPEMD160.new(sha).digest()
    five_bit = _bech32.convertbits(list(ripe), 8, 5)
    osmosis_address = _bech32.bech32_encode("osmosis", five_bit)

    assert verify_wallet_signature(
        chain="osmosis",
        message=message,
        signature="0x" + sig.hex(),
        public_key=None,
        expected_address=osmosis_address,
    )


def test_cosmos_hardcoded_cosmos_hrp_fails_for_osmosis_address():
    """Sanity check: the old hardcoded 'cosmos' HRP would have rejected osmosis addresses."""
    import hashlib
    import bech32 as _bech32
    from coincurve import PrivateKey, PublicKey
    from Crypto.Hash import RIPEMD160

    priv = PrivateKey(hashlib.sha256(b"osmosis-hrp-regression").digest())
    message = "pocketagent:reissue:test-agent:1740000000"
    msg_bytes = message.encode("utf-8")
    prefix = b"\x19\x00" + len(msg_bytes).to_bytes(4, "big") + hashlib.sha256(msg_bytes).digest()
    to_sign = hashlib.sha256(prefix).digest()
    sig = priv.sign_recoverable(to_sign, hasher=None)
    vk = PublicKey.from_signature_and_message(sig, to_sign, hasher=None)
    uncompressed = vk.format(compressed=False)
    sha = hashlib.sha256(uncompressed[1:]).digest()
    ripe = RIPEMD160.new(sha).digest()
    five_bit = _bech32.convertbits(list(ripe), 8, 5)
    osmosis_address = _bech32.bech32_encode("osmosis", five_bit)

    # Submit the same signature under chain="cosmos" with the osmosis address.
    # Should fail because the address starts with "osmosis1" not "cosmos1".
    assert not verify_wallet_signature(
        chain="cosmos",
        message=message,
        signature="0x" + sig.hex(),
        public_key=None,
        expected_address=osmosis_address,
    )
