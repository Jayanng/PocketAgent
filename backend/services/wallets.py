from __future__ import annotations

from typing import Any

from eth_account import Account

try:
    from .encryption import encrypt_private_key
    from .chain_registry import get_chain_metadata
    from ..database import update_agent
except ImportError:
    from services.encryption import encrypt_private_key
    from services.chain_registry import get_chain_metadata
    from database import update_agent


WRITE_PROTOCOLS = {"evm", "solana", "tron", "sui", "cosmos", "near"}


def _create_evm_wallet() -> dict[str, str]:
    account = Account.create()
    return {
        "address": account.address,
        "encrypted_private_key": encrypt_private_key(account.key.hex()),
    }


def _create_solana_wallet() -> dict[str, str]:
    from solders.keypair import Keypair

    keypair = Keypair()
    return {
        "address": str(keypair.pubkey()),
        "encrypted_private_key": encrypt_private_key(bytes(keypair).hex()),
    }


def _create_tron_wallet() -> dict[str, str]:
    from tronpy.keys import PrivateKey

    key = PrivateKey.random()
    return {
        "address": key.public_key.to_base58check_address(),
        "encrypted_private_key": encrypt_private_key(key.hex()),
    }


def _create_sui_wallet() -> dict[str, str]:
    from pysui.sui.sui_crypto import SignatureScheme, create_new_address

    _, keypair, address = create_new_address(SignatureScheme.ED25519)
    return {
        "address": str(address),
        "encrypted_private_key": encrypt_private_key(keypair.serialize()),
    }


def _create_cosmos_wallet() -> dict[str, str]:
    from cosmpy.aerial.wallet import LocalWallet

    wallet = LocalWallet.generate(prefix="cosmos")
    return {
        "address": str(wallet.address()),
        "encrypted_private_key": encrypt_private_key(wallet.signer().private_key_hex),
    }


def _create_near_wallet() -> dict[str, str]:
    import base58
    from nacl.signing import SigningKey

    signing_key = SigningKey.generate()
    public_key_bytes = bytes(signing_key.verify_key)
    private_key_bytes = bytes(signing_key)
    return {
        "address": public_key_bytes.hex(),
        "encrypted_private_key": encrypt_private_key(
            f"ed25519:{base58.b58encode(private_key_bytes).decode()}"
        ),
    }


_PROTOCOL_CREATORS = {
    "evm": _create_evm_wallet,
    "solana": _create_solana_wallet,
    "tron": _create_tron_wallet,
    "sui": _create_sui_wallet,
    "cosmos": _create_cosmos_wallet,
    "near": _create_near_wallet,
}


def create_protocol_wallet(protocol: str) -> dict[str, str]:
    creator = _PROTOCOL_CREATORS.get(protocol)
    if creator is None:
        raise ValueError(f"Unsupported write protocol: {protocol}")
    return creator()


def create_agent_wallets() -> dict[str, dict[str, str]]:
    """Create encrypted protocol wallets for live write-capable protocols."""
    return {protocol: create_protocol_wallet(protocol) for protocol in sorted(WRITE_PROTOCOLS)}


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


def missing_write_protocols(agent: dict[str, Any]) -> list[str]:
    addresses = agent.get("wallet_addresses") or {}
    encrypted = agent.get("encrypted_wallets") or {}
    if not isinstance(addresses, dict):
        addresses = {}
    if not isinstance(encrypted, dict):
        encrypted = {}

    missing: list[str] = []
    for protocol in sorted(WRITE_PROTOCOLS):
        has_address = bool(addresses.get(protocol))
        has_key = bool(encrypted.get(protocol))
        if protocol == "evm" and not has_key and agent.get("encrypted_private_key"):
            has_key = True
        if protocol == "evm" and not has_address and agent.get("wallet_address"):
            has_address = True
        if not has_address or not has_key:
            missing.append(protocol)
    return missing


async def ensure_agent_write_wallets(db: Any, agent: dict[str, Any]) -> dict[str, Any]:
    """Add any missing write-protocol wallets (e.g. Sui on pre-upgrade agents)."""
    missing = missing_write_protocols(agent)
    if not missing:
        return agent

    addresses = dict(agent.get("wallet_addresses") or {})
    encrypted = dict(agent.get("encrypted_wallets") or {})
    updates: dict[str, Any] = {}

    for protocol in missing:
        wallet = create_protocol_wallet(protocol)
        addresses[protocol] = wallet["address"]
        encrypted[protocol] = wallet["encrypted_private_key"]
        if protocol == "evm":
            updates["wallet_address"] = wallet["address"]

    updates["wallet_addresses"] = addresses
    updates["encrypted_wallets"] = encrypted
    updated = await update_agent(db, str(agent["id"]), **updates)
    return updated or agent


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