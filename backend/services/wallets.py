from __future__ import annotations

from typing import Any

from eth_account import Account

try:
    from .encryption import encrypt_private_key
    from .chain_registry import get_chain_metadata
except ImportError:
    from services.encryption import encrypt_private_key
    from services.chain_registry import get_chain_metadata


WRITE_PROTOCOLS = {"evm", "solana", "tron"}


def create_agent_wallets() -> dict[str, dict[str, str]]:
    """Create encrypted protocol wallets for live write-capable protocols."""
    evm_account = Account.create()

    from solders.keypair import Keypair
    from tronpy.keys import PrivateKey

    solana_keypair = Keypair()
    tron_key = PrivateKey.random()

    return {
        "evm": {
            "address": evm_account.address,
            "encrypted_private_key": encrypt_private_key(evm_account.key.hex()),
        },
        "solana": {
            "address": str(solana_keypair.pubkey()),
            "encrypted_private_key": encrypt_private_key(bytes(solana_keypair).hex()),
        },
        "tron": {
            "address": tron_key.public_key.to_base58check_address(),
            "encrypted_private_key": encrypt_private_key(tron_key.hex()),
        },
    }


def wallet_maps(wallets: dict[str, dict[str, str]]) -> tuple[dict[str, str], dict[str, str]]:
    encrypted_wallets = {
        protocol: wallet["encrypted_private_key"]
        for protocol, wallet in wallets.items()
    }
    wallet_addresses = {
        protocol: wallet["address"]
        for protocol, wallet in wallets.items()
    }
    return encrypted_wallets, wallet_addresses


def wallet_address_for_chain(agent: dict[str, Any], chain: str) -> str | None:
    protocol = get_chain_metadata(chain)["protocol"]
    addresses = agent.get("wallet_addresses") or {}
    if isinstance(addresses, dict):
        address = addresses.get(protocol)
        if address:
            return str(address)
    if protocol == "evm":
        legacy = agent.get("wallet_address")
        return str(legacy) if legacy else None
    return None
