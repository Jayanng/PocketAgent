from __future__ import annotations

from typing import Any

try:
    from .chain_registry import get_chain_metadata
except ImportError:
    from services.chain_registry import get_chain_metadata

SUI_COIN_TYPE = "0x2::sui::SUI"
NATIVE_SUI_COIN_STRUCT = "0x2::coin::Coin<0x2::sui::SUI>"
# Pocket lacks the index store for suix_getCoins / suix_getOwnedObjects.
DEFAULT_SUI_BOOTSTRAP_RPC = "https://fullnode.mainnet.sui.io:443"
DEFAULT_SUI_WRITE_RPC = "https://sui.api.pocket.network"
# Reserve headroom for gas when picking a coin object (MIST).
SUI_GAS_BUFFER_MIST = 5_000_000


def sui_write_rpc_url(chain: str = "sui") -> str:
    metadata = get_chain_metadata(chain)
    write_url = metadata.get("write_url")
    if isinstance(write_url, str) and write_url.strip():
        return write_url.strip()
    return DEFAULT_SUI_WRITE_RPC


def _is_native_sui_coin_type(object_type: str | None) -> bool:
    if not object_type:
        return False
    return object_type == SUI_COIN_TYPE or object_type == NATIVE_SUI_COIN_STRUCT or (
        "0x2::coin::Coin" in object_type and "0x2::sui::SUI" in object_type
    )


def _sui_coin_entries(coins_result: Any) -> list[Any]:
    if not coins_result.is_ok():
        detail = coins_result.result_string or "unknown error"
        raise RuntimeError(f"Failed to fetch SUI coin objects: {detail}")

    payload = coins_result.result_data
    if payload is None:
        return []
    if hasattr(payload, "data"):
        return list(payload.data or [])
    if isinstance(payload, list):
        return payload
    return []


def _coin_to_tracked_record(coin: Any) -> dict[str, Any]:
    return {
        "coin_object_id": str(getattr(coin, "coin_object_id", getattr(coin, "object_id", ""))),
        "balance": int(getattr(coin, "balance", 0) or 0),
        "version": str(getattr(coin, "version", "")),
        "digest": str(getattr(coin, "digest", "")),
    }


def _tracked_records_from_coin_objects(coin_objects: list[Any]) -> list[dict[str, Any]]:
    return [_coin_to_tracked_record(coin) for coin in coin_objects]


def _tracked_coin_ids(tracked_coins: list[dict[str, Any]]) -> list[str]:
    return [
        str(entry["coin_object_id"])
        for entry in tracked_coins
        if isinstance(entry.get("coin_object_id"), str) and entry["coin_object_id"]
    ]


def _apply_object_changes_to_coin_ids(
    coin_ids: set[str],
    object_changes: list[dict[str, Any]] | None,
    *,
    sender: str | None = None,
) -> set[str]:
    updated = set(coin_ids)
    for change in object_changes or []:
        if not isinstance(change, dict):
            continue
        change_type = change.get("type")
        object_id = change.get("objectId")
        if not object_id:
            continue
        if change_type == "deleted":
            updated.discard(str(object_id))
            continue
        if change_type != "created":
            continue
        if not _is_native_sui_coin_type(str(change.get("objectType") or "")):
            continue
        owner = change.get("owner") or {}
        if sender and isinstance(owner, dict):
            address_owner = owner.get("AddressOwner")
            if address_owner and str(address_owner) != str(sender):
                continue
        updated.add(str(object_id))
    return updated


def _select_sui_coin(coins: list[Any], amount_mist: int) -> Any:
    if not coins:
        raise RuntimeError(
            "No SUI coin objects found for this wallet. "
            "Fund the agent Sui address, then retry."
        )

    required = amount_mist + SUI_GAS_BUFFER_MIST
    best = None
    best_balance = -1
    for coin in coins:
        balance = int(getattr(coin, "balance", 0) or 0)
        if balance >= required:
            return coin
        if balance > best_balance:
            best = coin
            best_balance = balance

    if best is not None and best_balance >= amount_mist:
        return best

    raise RuntimeError(
        f"Insufficient SUI balance for transfer: need at least {amount_mist} MIST "
        f"(plus gas), largest coin has {max(best_balance, 0)} MIST."
    )


def _extract_tx_digest(result_data: Any) -> str:
    if result_data is None:
        raise RuntimeError("Sui execute returned no transaction data.")
    digest = getattr(result_data, "digest", None)
    if digest:
        return str(digest)
    if isinstance(result_data, dict):
        digest = result_data.get("digest")
        if digest:
            return str(digest)
    raise RuntimeError(f"Sui execute succeeded but no digest was returned: {result_data!r}")


def _wrap_coin_objects_for_gas(coin_objects: list[Any]) -> Any:
    from pysui.sui.sui_clients.common import SuiRpcResult
    from pysui.sui.sui_txresults.single_tx import SuiCoinObjects

    return SuiRpcResult(True, "", SuiCoinObjects(data=coin_objects))


def _bootstrap_tracked_coins_mysten(keystring: str, sender: Any) -> list[dict[str, Any]]:
    from pysui import SuiConfig, SyncClient

    config = SuiConfig.user_config(rpc_url=DEFAULT_SUI_BOOTSTRAP_RPC, prv_keys=[keystring])
    client = SyncClient(config)
    coins = client.get_coin(SUI_COIN_TYPE, sender, fetch_all=True)
    coin_list = _sui_coin_entries(coins)
    if not coin_list:
        return []
    return _tracked_records_from_coin_objects(coin_list)


def _refresh_tracked_coins_pocket(client: Any, tracked_coins: list[dict[str, Any]]) -> list[Any]:
    from pysui.sui.sui_txresults.single_tx import SuiCoinObject

    refreshed: list[Any] = []
    for entry in tracked_coins:
        coin_id = entry.get("coin_object_id")
        if not coin_id:
            continue
        result = client.get_object(str(coin_id))
        if not result.is_ok() or result.result_data is None:
            continue
        obj = result.result_data
        if not _is_native_sui_coin_type(getattr(obj, "object_type", None)):
            continue
        refreshed.append(SuiCoinObject.from_read_object(obj))
    return refreshed


def _resolve_sui_coin_objects(
    pocket_client: Any,
    keystring: str,
    sender: Any,
    tracked_coins: list[dict[str, Any]],
) -> tuple[list[Any], list[dict[str, Any]]]:
    tracked = list(tracked_coins)
    coin_objects = _refresh_tracked_coins_pocket(pocket_client, tracked)
    if coin_objects:
        return coin_objects, _tracked_records_from_coin_objects(coin_objects)

    if not _tracked_coin_ids(tracked):
        tracked = _bootstrap_tracked_coins_mysten(keystring, sender)
        coin_objects = _refresh_tracked_coins_pocket(pocket_client, tracked)

    if not coin_objects:
        raise RuntimeError(
            "No SUI coin objects found for this wallet. "
            "Fund the agent Sui address, then retry."
        )
    return coin_objects, _tracked_records_from_coin_objects(coin_objects)


def _sync_tracked_coins_after_execute(
    pocket_client: Any,
    sender: Any,
    tracked_coins: list[dict[str, Any]],
    result_data: Any,
) -> list[dict[str, Any]]:
    coin_ids = set(_tracked_coin_ids(tracked_coins))
    object_changes = getattr(result_data, "object_changes", None)
    if isinstance(object_changes, list):
        coin_ids = _apply_object_changes_to_coin_ids(coin_ids, object_changes, sender=str(sender))

    refreshed_entries = [
        {"coin_object_id": coin_id, "balance": 0, "version": "", "digest": ""}
        for coin_id in sorted(coin_ids)
    ]
    coin_objects = _refresh_tracked_coins_pocket(pocket_client, refreshed_entries)
    return _tracked_records_from_coin_objects(coin_objects)


def execute_sui_native_transfer(
    rpc_url: str,
    keystring: str,
    to_address: str,
    amount_mist: int,
    tracked_coins: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from pysui import SuiAddress, SuiConfig, SyncClient
    from pysui.sui.sui_txn.sync_transaction import SuiTransaction

    if amount_mist <= 0:
        raise ValueError("Sui transfer amount must be positive.")

    write_rpc = rpc_url.strip() if isinstance(rpc_url, str) and rpc_url.strip() else sui_write_rpc_url()
    pocket_config = SuiConfig.user_config(rpc_url=write_rpc, prv_keys=[keystring])
    pocket_client = SyncClient(pocket_config)
    sender = pocket_config.active_address
    if not sender:
        raise RuntimeError("Sui sender address is not configured for signing.")

    coin_objects, tracked_records = _resolve_sui_coin_objects(
        pocket_client,
        keystring,
        sender,
        list(tracked_coins or []),
    )
    coin = _select_sui_coin(coin_objects, amount_mist)
    coins_for_gas = _wrap_coin_objects_for_gas(coin_objects)
    pocket_client.get_gas = lambda address=None, fetch_all=False: coins_for_gas

    txer = SuiTransaction(client=pocket_client, initial_sender=sender)
    txer.transfer_sui(
        recipient=SuiAddress(to_address),
        from_coin=coin.coin_object_id,
        amount=amount_mist,
    )
    result = txer.execute(options={"showEffects": True, "showObjectChanges": True})
    if not result.is_ok():
        raise RuntimeError(f"Sui execute failed: {result.result_string or result}")

    digest = _extract_tx_digest(result.result_data)
    if hasattr(result.result_data, "succeeded") and not result.result_data.succeeded:
        raise RuntimeError(f"Sui transaction failed on-chain: {result.result_data.status}")

    updated_tracked = _sync_tracked_coins_after_execute(
        pocket_client,
        sender,
        tracked_records,
        result.result_data,
    )

    return {
        "from": str(sender),
        "tx_hash": digest,
        "amount_mist": amount_mist,
        "rpc_url": write_rpc,
        "tracked_coins": updated_tracked,
    }