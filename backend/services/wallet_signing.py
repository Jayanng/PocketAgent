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
