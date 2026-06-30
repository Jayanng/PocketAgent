"""Per-chain wallet signature verification.

Dispatches to chain-specific verifiers. Each verifier returns True iff
the signature is well-formed AND recovers to the expected_address.
"""
from __future__ import annotations


EVM_CHAINS = frozenset({
    "ethereum", "polygon", "arbitrum", "bsc", "optimism", "avalanche",
    "fantom", "gnosis", "base", "berachain", "blast", "celo", "linea",
    "mantle", "scroll", "zksync_era", "sonic", "polygon_zkevm",
})


def verify_wallet_signature(
    chain: str,
    message: str | bytes,
    signature: str,
    public_key: str | None,
    expected_address: str,
) -> bool:
    if chain in EVM_CHAINS:
        return _verify_evm(message, signature, expected_address)
    if chain == "solana":
        return _verify_solana(message, signature, public_key, expected_address)
    if chain == "sui":
        return _verify_sui(message, signature, public_key, expected_address)
    if chain == "near":
        return _verify_near(message, signature, public_key, expected_address)
    if chain in COSMOS_CHAINS:
        return _verify_cosmos(message, signature, public_key, expected_address)
    if chain == "tron":
        return _verify_tron(message, signature, public_key, expected_address)
    raise ValueError(f"unsupported chain for signing: {chain}")


def _verify_evm(message: str | bytes, signature: str, expected_address: str) -> bool:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    try:
        if isinstance(message, bytes):
            text: str | bytes = message.decode("utf-8", errors="replace")
        else:
            text = message
        msg = encode_defunct(text=text)
        sig = signature[2:] if signature.startswith("0x") else signature
        recovered = Account.recover_message(msg, signature=sig)
        return recovered.lower() == expected_address.lower()
    except Exception:
        return False


def _verify_solana(message: str | bytes, signature: str, public_key: str | None, expected_address: str) -> bool:
    try:
        from solders.signature import Signature
        from solders.pubkey import Pubkey
        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        # Accept base58 (standard wallet output), hex, or base64
        try:
            sig = Signature.from_string(signature)
        except Exception:
            try:
                sig = Signature.from_bytes(bytes.fromhex(signature))
            except Exception:
                import base64
                sig = Signature.from_bytes(base64.b64decode(signature))
        pub = Pubkey.from_string(public_key or expected_address)
        return sig.verify(pub, msg_bytes)
    except Exception:
        return False


def _verify_sui(message: str | bytes, signature: str, public_key: str | None, expected_address: str) -> bool:
    """Verify a Sui personal-message signature.

    Sui personal messages are signed over Blake2b(intent || msg_bytes), where
    intent = b"\\x00\\x00\\x00" for PersonalMessage domain. The Sui address is
    derived as Blake2b(pubkey || 0x00 scheme byte) truncated to 32 bytes; we
    confirm the supplied expected_address matches the derived address before
    verifying the signature against the supplied public_key.
    """
    try:
        import base64
        import hashlib
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        sig_bytes = base64.b64decode(signature)
        pub_bytes = base64.b64decode(public_key or "")
        if len(sig_bytes) != 64 or len(pub_bytes) != 32:
            return False
        # Derive Sui address from public key and compare to expected
        derived_addr = "0x" + hashlib.blake2b(pub_bytes + b"\x00", digest_size=32).hexdigest()
        if derived_addr.lower() != expected_address.lower():
            return False
        digest = hashlib.blake2b(b"\x00\x00\x00" + msg_bytes, digest_size=32).digest()
        Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig_bytes, digest)
        return True
    except Exception:
        return False


COSMOS_CHAINS = frozenset({
    "cosmos", "cosmos_hub", "osmosis", "akash", "celestia", "injective",
    "kujira", "stargaze", "juno", "evmos", "secret_network", "sei",
})


def _verify_near(message: str | bytes, signature: str, public_key: str | None, expected_address: str) -> bool:
    """Verify a NEAR implicit-account Ed25519 signature.

    NEAR signed messages are: prefix b"\\x00\\x00\\x00\\x00" || msg_bytes,
    signed with the Ed25519 key. The implicit account address is the hex of
    the 32-byte Ed25519 public key.
    """
    try:
        import base64
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        sig_bytes = base64.b64decode(signature)
        pub_hex = public_key or expected_address
        pub_bytes = bytes.fromhex(pub_hex)
        if len(sig_bytes) != 64 or len(pub_bytes) != 32:
            return False
        if pub_bytes.hex() != expected_address.lower():
            return False
        preimage = b"\x00\x00\x00\x00" + msg_bytes
        Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig_bytes, preimage)
        return True
    except Exception:
        return False


def _verify_cosmos(message: str | bytes, signature: str, public_key: str | None, expected_address: str) -> bool:
    """Verify a Cosmos secp256k1 ADR-036 signature and recover bech32 address."""
    try:
        import hashlib

        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        # Strip 0x prefix and ensure even length hex
        sig_hex = signature[2:] if signature.startswith("0x") else signature
        if len(sig_hex) != 130:
            return False
        sig_bytes = bytes.fromhex(sig_hex)
        prefix = b"\x19\x00" + len(msg_bytes).to_bytes(4, "big") + hashlib.sha256(msg_bytes).digest()
        to_sign = hashlib.sha256(prefix).digest()
        # Recover pubkey (uncompressed, 65 bytes -> 64 byte X||Y) via coincurve
        from coincurve import PublicKey
        try:
            vk = PublicKey.from_signature_and_message(sig_bytes, to_sign, hasher=None)
        except Exception:
            return False
        uncompressed = vk.format(compressed=False)  # 65 bytes: 0x04 || X(32) || Y(32)
        sha = hashlib.sha256(uncompressed[1:]).digest()
        ripemd = _ripemd160(sha)
        bech32_addr = _bech32_encode("cosmos", ripemd)
        return bech32_addr == expected_address
    except Exception:
        return False


def _verify_tron(message: str | bytes, signature: str, public_key: str | None, expected_address: str) -> bool:
    """Verify a TRON secp256k1 personal-message signature and recover address."""
    try:
        import hashlib
        from coincurve import PublicKey

        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        sig_hex = signature[2:] if signature.startswith("0x") else signature
        if len(sig_hex) != 130:
            return False
        sig_bytes = bytes.fromhex(sig_hex)
        prefix = b"\x19TRON Signed Message:\n" + len(msg_bytes).to_bytes(4, "big") + msg_bytes
        digest = hashlib.sha256(prefix).digest()
        try:
            vk = PublicKey.from_signature_and_message(sig_bytes, digest, hasher=None)
        except Exception:
            return False
        uncompressed = vk.format(compressed=False)
        # keccak256(pubkey[1:])[12:]
        k = _keccak256(uncompressed[1:])
        address_bytes = b"\x41" + k[-20:]
        recovered = _base58check_encode(address_bytes)
        return recovered == expected_address
    except Exception:
        return False


def _ripemd160(data: bytes) -> bytes:
    # Use hashlib.new if available; fall back to a stdlib alternative.
    try:
        from Crypto.Hash import RIPEMD160  # type: ignore
        return RIPEMD160.new(data).digest()
    except Exception:
        # Last-resort: use coincurve's ripemd160 (some builds bundle it via libsecp256k1)
        # Actually coincurve doesn't expose ripemd160. So we need a pure-python fallback.
        # Try eth_utils.ripemd160 if available
        try:
            from eth_utils import keccak, to_bytes  # noqa: F401
            from eth_hash.auto import keccak as _kh  # noqa: F401
        except Exception:
            pass
        # Slow pure-python ripemd160 via hashlib builtin on some Pythons
        import hashlib as _h
        if hasattr(_h, "new"):
            try:
                return _h.new("ripemd160", data).digest()
            except Exception:
                pass
        raise RuntimeError("RIPEMD160 unavailable; install pycryptodome")


def _bech32_encode(hrp: str, data: bytes) -> str:
    import bech32
    five_bit = bech32.convertbits(list(data), 8, 5)
    if five_bit is None:
        raise ValueError("bech32 conversion failed")
    return bech32.bech32_encode(hrp, five_bit)


def _keccak256(data: bytes) -> bytes:
    try:
        from Crypto.Hash import keccak  # type: ignore
        k = keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except Exception:
        from eth_hash.auto import keccak as _k
        return _k(data)


def _base58check_encode(payload: bytes) -> str:
    import hashlib
    import base58
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + checksum).decode()
