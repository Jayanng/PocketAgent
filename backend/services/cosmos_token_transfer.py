from __future__ import annotations

from typing import Any

try:
    from .chain_registry import get_chain_metadata
    from .cosmos_transfer import cosmos_network_config, _private_key_from_hex
except ImportError:
    from services.chain_registry import get_chain_metadata
    from services.cosmos_transfer import cosmos_network_config, _private_key_from_hex


def execute_cosmos_ibc_transfer(
    chain: str,
    private_key_hex: str,
    to_address: str,
    amount_base: int,
    denom: str,
) -> dict[str, Any]:
    """Transfer a non-staking / IBC denom via the Cosmos SDK ``bank`` module.

    This is identical to a native ``send_tokens`` call — the only difference is
    that the ``denom`` is an arbitrary IBC denom string (e.g. ``ibc/...``)
    rather than the chain's staking denom.
    """
    from cosmpy.aerial.client import LedgerClient
    from cosmpy.aerial.wallet import LocalWallet

    if amount_base <= 0:
        raise ValueError("Cosmos IBC transfer amount must be positive.")
    if not denom:
        raise ValueError("Cosmos IBC transfer requires a non-empty denom.")

    metadata = get_chain_metadata(chain)
    bech32_prefix = str(metadata.get("cosmos_bech32_prefix") or "cosmos")
    network = cosmos_network_config(chain)
    ledger = LedgerClient(network)
    wallet = LocalWallet(_private_key_from_hex(private_key_hex), prefix=bech32_prefix)
    sender_address = wallet.address()

    tx = ledger.send_tokens(to_address, amount_base, denom, wallet)
    tx_hash = str(getattr(tx, "tx_hash", "") or "")
    if not tx_hash:
        raise RuntimeError(f"Cosmos IBC broadcast returned no tx hash: {tx!r}")

    return {
        "from": str(sender_address),
        "tx_hash": tx_hash,
        "amount_base": amount_base,
        "denom": denom,
        "chain_id": network.chain_id,
    }


def execute_cosmos_cw20_transfer(
    chain: str,
    private_key_hex: str,
    contract_address: str,
    to_address: str,
    amount_raw: int,
) -> dict[str, Any]:
    """Transfer CW20 (CosmWasm) tokens by executing a ``transfer`` message on
    the contract."""
    return execute_cosmos_contract_call(
        chain,
        private_key_hex,
        contract_address,
        {"transfer": {"recipient": to_address, "amount": str(amount_raw)}},
    )


def execute_cosmos_contract_call(
    chain: str,
    private_key_hex: str,
    contract_address: str,
    msg: dict[str, Any],
) -> dict[str, Any]:
    """Execute an arbitrary CosmWasm ``ExecuteMsg`` on a contract (write)."""
    from cosmpy.aerial.client import LedgerClient
    from cosmpy.aerial.contract import LedgerContract
    from cosmpy.aerial.wallet import LocalWallet
    from cosmpy.crypto.address import Address

    if not isinstance(msg, dict):
        raise ValueError("Cosmos contract execute msg must be a JSON object.")

    metadata = get_chain_metadata(chain)
    bech32_prefix = str(metadata.get("cosmos_bech32_prefix") or "cosmos")
    network = cosmos_network_config(chain)
    ledger = LedgerClient(network)
    wallet = LocalWallet(_private_key_from_hex(private_key_hex), prefix=bech32_prefix)
    sender_address = wallet.address()

    contract = LedgerContract(
        None,
        ledger,
        address=Address(contract_address, prefix=bech32_prefix),
    )
    submitted = contract.execute(msg, sender=wallet)
    tx_hash = str(getattr(submitted, "tx_hash", "") or "")
    if not tx_hash:
        raise RuntimeError(f"Cosmos contract execute returned no tx hash: {submitted!r}")

    return {
        "from": str(sender_address),
        "tx_hash": tx_hash,
        "contract_address": contract_address,
        "msg": msg,
        "chain_id": network.chain_id,
    }


def cosmos_cw20_query(
    chain: str,
    private_key_hex: str,
    contract_address: str,
    query_msg: dict[str, Any],
) -> Any:
    """Run a CosmWasm ``SmartQuery`` against a contract (read-only)."""
    from cosmpy.aerial.client import LedgerClient
    from cosmpy.aerial.contract import LedgerContract
    from cosmpy.aerial.wallet import LocalWallet
    from cosmpy.crypto.address import Address

    metadata = get_chain_metadata(chain)
    bech32_prefix = str(metadata.get("cosmos_bech32_prefix") or "cosmos")
    network = cosmos_network_config(chain)
    ledger = LedgerClient(network)
    wallet = LocalWallet(_private_key_from_hex(private_key_hex), prefix=bech32_prefix)

    contract = LedgerContract(
        None,
        ledger,
        address=Address(contract_address, prefix=bech32_prefix),
    )
    return contract.query(query_msg)
