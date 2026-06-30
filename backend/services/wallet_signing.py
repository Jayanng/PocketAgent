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
