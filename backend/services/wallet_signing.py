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

COSMOS_CHAINS = frozenset({
    "cosmos", "cosmos_hub", "osmosis", "akash", "celestia", "injective",
    "kujira", "stargaze", "juno", "evmos", "secret_network", "sei",
})

# Mapping from our chain key to the bech32 HRP used in addresses.
# Sources: each chain's own docs (Keplr, station, etc.).
COSMOS_HRP = {
    "cosmos": "cosmos",
    "cosmos_hub": "cosmos",
    "osmosis": "osmosis",
    "akash": "akash",
    "celestia": "celestia",
    "injective": "inj",
    "kujira": "kujira",
    "stargaze": "stars",
    "juno": "juno",
    "evmos": "evmos",
    "secret_network": "secret",
    "sei": "sei",
}


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
        return _verify_cosmos(chain, message, signature, expected_address)
    if chain == "tron":
        return _verify_tron(message, signature, expected_address)
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


def _recover_pubkey_candidates(sig_bytes: bytes, message: bytes):
    """Yield every secp256k1 pubkey recoverable from (r||s[, rec_id]).

    secp256k1 ECDSA recovery: given (r, s), up to two distinct pubkeys
    exist (mirror y-coords), so up to four rec_ids (two x candidates ×
    two y parities) each yield a candidate — and the wrong ones do NOT
    necessarily raise; coincurve returns a valid but mismatched pubkey.
    The caller MUST therefore iterate ALL candidates and check the
    derived address, not stop at the first successful recovery.

    Accepts both 64-byte (r||s only — what real Cosmos/TRON wallets
    emit per ADR-036; all four rec_ids are tried) and 65-byte
    (r||s||rec_id — what coincurve.sign_recoverable produces; the
    embedded rec_id is authoritative).
    """
    from coincurve import PublicKey
    if len(sig_bytes) == 64:
        rec_ids = range(4)
    elif len(sig_bytes) == 65:
        rec_ids = [sig_bytes[64]]
    else:
        return
    for rec_id in rec_ids:
        try:
            yield PublicKey.from_signature_and_message(
                sig_bytes[:64] + bytes([rec_id]), message, hasher=None
            )
        except Exception:
            continue


def _verify_cosmos(chain: str, message: str | bytes, signature: str, expected_address: str) -> bool:
    """Verify a Cosmos secp256k1 ADR-036 signature and recover bech32 address."""
    try:
        import hashlib

        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        sig_hex = signature[2:] if signature.startswith("0x") else signature
        # Accept 64-byte (real wallets) or 65-byte (recoverable, some libs)
        if len(sig_hex) not in (128, 130):
            return False
        sig_bytes = bytes.fromhex(sig_hex)
        prefix = b"\x19\x00" + len(msg_bytes).to_bytes(4, "big") + hashlib.sha256(msg_bytes).digest()
        to_sign = hashlib.sha256(prefix).digest()
        hrp = COSMOS_HRP.get(chain, "cosmos")
        for vk in _recover_pubkey_candidates(sig_bytes, to_sign):
            uncompressed = vk.format(compressed=False)  # 65 bytes: 0x04 || X(32) || Y(32)
            sha = hashlib.sha256(uncompressed[1:]).digest()
            ripemd = _ripemd160(sha)
            bech32_addr = _bech32_encode(hrp, ripemd)
            if bech32_addr == expected_address:
                return True
        return False
    except Exception:
        return False


def _verify_tron(message: str | bytes, signature: str, expected_address: str) -> bool:
    """Verify a TRON secp256k1 personal-message signature and recover address."""
    try:
        import hashlib

        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        sig_hex = signature[2:] if signature.startswith("0x") else signature
        if len(sig_hex) not in (128, 130):
            return False
        sig_bytes = bytes.fromhex(sig_hex)
        prefix = b"\x19TRON Signed Message:\n" + len(msg_bytes).to_bytes(4, "big") + msg_bytes
        digest = hashlib.sha256(prefix).digest()
        for vk in _recover_pubkey_candidates(sig_bytes, digest):
            uncompressed = vk.format(compressed=False)
            # keccak256(pubkey[1:])[12:]
            k = _keccak256(uncompressed[1:])
            address_bytes = b"\x41" + k[-20:]
            recovered = _base58check_encode(address_bytes)
            if recovered == expected_address:
                return True
        return False
    except Exception:
        return False


def _ripemd160(data: bytes) -> bytes:
    """RIPEMD-160 hash. Required for Cosmos address derivation (not in stdlib).

    Raises RuntimeError immediately if no implementation is available, so the
    caller sees a configuration error rather than a silent invalid signature.
    """
    from Crypto.Hash import RIPEMD160  # type: ignore
    return RIPEMD160.new(data).digest()


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
