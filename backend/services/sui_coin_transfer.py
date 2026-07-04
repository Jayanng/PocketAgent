from __future__ import annotations

from typing import Any

try:
    from .sui_transfer import (
        DEFAULT_SUI_BOOTSTRAP_RPC,
        SUI_COIN_TYPE,
        _extract_tx_digest,
        _resolve_sui_coin_objects,
        _select_sui_coin,
        _wrap_coin_objects_for_gas,
        sui_write_rpc_url,
    )
except ImportError:
    from services.sui_transfer import (
        DEFAULT_SUI_BOOTSTRAP_RPC,
        SUI_COIN_TYPE,
        _extract_tx_digest,
        _resolve_sui_coin_objects,
        _select_sui_coin,
        _wrap_coin_objects_for_gas,
        sui_write_rpc_url,
    )


def _fetch_coins_by_type(bootstrap_url: str, sender: str, coin_type: str) -> list[dict[str, Any]]:
    """Fetch coin objects of a specific type via ``suix_getCoins``.

    Pocket's SUI endpoint lacks the index store for ``suix_getCoins``, so we
    bootstrap from the public Mysten fullnode (read-only) — the same approach
    the native SUI transfer uses for owned-object discovery.
    """
    import httpx

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "suix_getCoins",
        "params": [sender, coin_type],
    }
    resp = httpx.post(bootstrap_url, json=payload, timeout=30.0)
    resp.raise_for_status()
    body = resp.json()
    result = body.get("result")
    if not isinstance(result, dict):
        return []
    return list(result.get("data", []) or [])


def _select_target_coin_id(coins: list[dict[str, Any]], amount: int) -> str:
    """Pick a coin object id whose balance covers ``amount``."""
    best_id: str | None = None
    best_balance = -1
    for coin in coins:
        balance = int(coin.get("balance", 0) or 0)
        coin_id = coin.get("coinObjectId") or coin.get("coin_object_id")
        if not coin_id:
            continue
        if balance >= amount:
            return str(coin_id)
        if balance > best_balance:
            best_id = str(coin_id)
            best_balance = balance
    if best_id is not None:
        raise RuntimeError(
            f"Insufficient coin balance: need {amount}, largest coin has {max(best_balance, 0)}."
        )
    raise RuntimeError("No coin objects of the requested type were found for this wallet.")


def execute_sui_coin_transfer(
    rpc_url: str,
    keystring: str,
    to_address: str,
    amount: int,
    coin_type: str,
    tracked_coins: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transfer ``amount`` of a SUI Move coin type (``0x2::coin::Coin<T>``) to
    a recipient by splitting a coin object and transferring the result."""
    from pysui import SuiAddress, SuiConfig, SyncClient
    from pysui.sui.sui_txn.sync_transaction import SuiTransaction

    if amount <= 0:
        raise ValueError("Sui coin transfer amount must be positive.")
    if not coin_type:
        raise ValueError("Sui coin transfer requires a coin_type.")
    # Native SUI is handled by the dedicated native transfer path.
    if coin_type == SUI_COIN_TYPE or coin_type.endswith("::sui::SUI"):
        raise ValueError(
            "Use send_transaction for native SUI transfers; send_sui_token is for non-SUI coin types."
        )

    write_rpc = rpc_url.strip() if isinstance(rpc_url, str) and rpc_url.strip() else sui_write_rpc_url()
    pocket_config = SuiConfig.user_config(rpc_url=write_rpc, prv_keys=[keystring])
    pocket_client = SyncClient(pocket_config)
    sender = pocket_config.active_address
    if not sender:
        raise RuntimeError("Sui sender address is not configured for signing.")

    # Gas is always paid in SUI — resolve SUI coin objects for gas payment.
    gas_coin_objects, _tracked = _resolve_sui_coin_objects(
        pocket_client, keystring, sender, list(tracked_coins or [])
    )
    _select_sui_coin(gas_coin_objects, 0)  # surface insufficient-gas early
    coins_for_gas = _wrap_coin_objects_for_gas(gas_coin_objects)
    pocket_client.get_gas = lambda address=None, fetch_all=False: coins_for_gas

    # Resolve the target coin objects of the requested type from the bootstrap fullnode.
    target_coins = _fetch_coins_by_type(DEFAULT_SUI_BOOTSTRAP_RPC, str(sender), coin_type)
    coin_id = _select_target_coin_id(target_coins, amount)

    txer = SuiTransaction(client=pocket_client, initial_sender=sender)
    split_result = txer.split_coin(coin=coin_id, amounts=[amount])
    txer.transfer_objects(transfers=[split_result], recipient=SuiAddress(to_address))
    result = txer.execute(options={"showEffects": True, "showObjectChanges": True})
    if not result.is_ok():
        raise RuntimeError(f"Sui coin transfer failed: {result.result_string or result}")
    digest = _extract_tx_digest(result.result_data)
    if hasattr(result.result_data, "succeeded") and not result.result_data.succeeded:
        raise RuntimeError(f"Sui transaction failed on-chain: {result.result_data.status}")

    return {
        "from": str(sender),
        "tx_hash": digest,
        "amount": amount,
        "coin_type": coin_type,
        "rpc_url": write_rpc,
    }


def execute_sui_move_call(
    rpc_url: str,
    keystring: str,
    target: str,
    arguments: list[Any],
    type_arguments: list[str] | None = None,
    tracked_coins: list[dict[str, Any]] | None = None,
    *,
    inspect: bool = False,
) -> Any:
    """Call a SUI Move function. When ``inspect`` is True, runs a dev-inspect
    (read-only, no broadcast); otherwise signs and broadcasts."""
    from pysui import SuiConfig, SyncClient
    from pysui.sui.sui_txn.sync_transaction import SuiTransaction

    write_rpc = rpc_url.strip() if isinstance(rpc_url, str) and rpc_url.strip() else sui_write_rpc_url()
    pocket_config = SuiConfig.user_config(rpc_url=write_rpc, prv_keys=[keystring])
    pocket_client = SyncClient(pocket_config)
    sender = pocket_config.active_address
    if not sender:
        raise RuntimeError("Sui sender address is not configured for signing.")

    if not inspect:
        gas_coin_objects, _tracked = _resolve_sui_coin_objects(
            pocket_client, keystring, sender, list(tracked_coins or [])
        )
        coins_for_gas = _wrap_coin_objects_for_gas(gas_coin_objects)
        pocket_client.get_gas = lambda address=None, fetch_all=False: coins_for_gas

    txer = SuiTransaction(client=pocket_client, initial_sender=sender)
    txer.move_call(
        target=target,
        arguments=arguments,
        type_arguments=type_arguments or [],
    )
    if inspect:
        return txer.inspect_all()
    result = txer.execute(options={"showEffects": True})
    if not result.is_ok():
        raise RuntimeError(f"Sui move call failed: {result.result_string or result}")
    digest = _extract_tx_digest(result.result_data)
    return {
        "from": str(sender),
        "tx_hash": digest,
        "target": target,
        "rpc_url": write_rpc,
    }
