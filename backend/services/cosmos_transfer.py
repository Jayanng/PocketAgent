from __future__ import annotations

from typing import Any

try:
    from .chain_registry import get_chain_metadata
except ImportError:
    from services.chain_registry import get_chain_metadata

DEFAULT_COSMOS_FEE_GAS_PRICE = 0.025


def _private_key_from_hex(private_key_hex: str):
    from cosmpy.crypto.keypairs import PrivateKey

    clean = private_key_hex.removeprefix("0x")
    return PrivateKey(bytes.fromhex(clean))


def cosmos_address_from_private_key(private_key_hex: str, bech32_prefix: str) -> str:
    from cosmpy.aerial.wallet import LocalWallet

    wallet = LocalWallet(_private_key_from_hex(private_key_hex), prefix=bech32_prefix)
    return str(wallet.address())


def cosmos_network_config(chain: str):
    from cosmpy.aerial.client import NetworkConfig

    metadata = get_chain_metadata(chain)
    cosmos_chain_id = str(metadata.get("cosmos_chain_id") or metadata["chain_id"])
    denom = str(metadata.get("cosmos_denom") or "")
    if not denom:
        raise ValueError(f"Chain '{chain}' is missing cosmos_denom metadata.")
    lcd_url = metadata["url"].replace("https://", "rest+https://", 1)
    config = NetworkConfig(
        chain_id=cosmos_chain_id,
        url=lcd_url,
        fee_minimum_gas_price=DEFAULT_COSMOS_FEE_GAS_PRICE,
        fee_denomination=denom,
        staking_denomination=denom,
    )
    config.validate()
    return config


def execute_cosmos_native_transfer(
    chain: str,
    private_key_hex: str,
    recipient_address: str,
    amount_base: int,
) -> dict[str, Any]:
    from cosmpy.aerial.client import LedgerClient
    from cosmpy.aerial.wallet import LocalWallet

    if amount_base <= 0:
        raise ValueError("Cosmos transfer amount must be positive.")

    metadata = get_chain_metadata(chain)
    denom = str(metadata["cosmos_denom"])
    bech32_prefix = str(metadata.get("cosmos_bech32_prefix") or "cosmos")
    network = cosmos_network_config(chain)
    ledger = LedgerClient(network)

    wallet = LocalWallet(_private_key_from_hex(private_key_hex), prefix=bech32_prefix)
    sender_address = wallet.address()

    tx = ledger.send_tokens(recipient_address, amount_base, denom, wallet)
    tx_hash = str(getattr(tx, "tx_hash", "") or "")
    if not tx_hash:
        raise RuntimeError(f"Cosmos broadcast returned no tx hash: {tx!r}")

    return {
        "from": str(sender_address),
        "tx_hash": tx_hash,
        "amount_base": amount_base,
        "denom": denom,
        "chain_id": network.chain_id,
    }