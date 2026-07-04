from __future__ import annotations

import asyncio
from typing import Any

NEAR_RPC_URL = "https://near.api.pocket.network"

# NEP-141 requires a 1 yoctoNEAR attached deposit for ft_transfer.
NEP141_REQUIRED_DEPOSIT_YOCTO = 1
# 30 Tgas is a comfortable default for a single ft_transfer / function call.
DEFAULT_NEAR_FUNCTION_CALL_GAS = 30_000_000_000_000


def _extract_near_tx_hash(result: Any) -> str:
    tx_hash = getattr(getattr(result, "transaction", None), "hash", None)
    if not tx_hash and hasattr(result, "transaction_hash"):
        tx_hash = result.transaction_hash
    if not tx_hash:
        tx_hash = str(result)
    return str(tx_hash)


def execute_near_nep141_transfer(
    account_id: str,
    private_key: str,
    contract_id: str,
    receiver_id: str,
    amount_raw: int,
    rpc_addr: str = NEAR_RPC_URL,
) -> dict[str, Any]:
    """Transfer NEP-141 (NEAR fungible token) by calling ``ft_transfer``."""
    if int(amount_raw) <= 0:
        raise ValueError("NEP-141 transfer amount must be positive.")

    async def _send() -> dict[str, Any]:
        from py_near.account import Account

        account = Account(account_id, private_key, rpc_addr=rpc_addr)
        try:
            await account.startup()
            result = await account.function_call(
                contract_id,
                "ft_transfer",
                {"receiver_id": receiver_id, "amount": str(int(amount_raw))},
                gas=DEFAULT_NEAR_FUNCTION_CALL_GAS,
                amount=NEP141_REQUIRED_DEPOSIT_YOCTO,
            )
            return {
                "from": account_id,
                "tx_hash": _extract_near_tx_hash(result),
                "contract_id": contract_id,
                "amount_raw": int(amount_raw),
            }
        finally:
            await account.shutdown()

    return asyncio.run(_send())


def execute_near_contract_call(
    account_id: str,
    private_key: str,
    contract_id: str,
    method_name: str,
    args: dict[str, Any],
    deposit_yocto: int = 0,
    gas: int = DEFAULT_NEAR_FUNCTION_CALL_GAS,
    rpc_addr: str = NEAR_RPC_URL,
) -> dict[str, Any]:
    """Call an arbitrary write method on a NEAR contract (function_call)."""
    if not isinstance(args, dict):
        raise ValueError("NEAR contract call args must be a JSON object.")

    async def _send() -> dict[str, Any]:
        from py_near.account import Account

        account = Account(account_id, private_key, rpc_addr=rpc_addr)
        try:
            await account.startup()
            result = await account.function_call(
                contract_id,
                method_name,
                args,
                gas=gas,
                amount=int(deposit_yocto),
            )
            return {
                "from": account_id,
                "tx_hash": _extract_near_tx_hash(result),
                "contract_id": contract_id,
                "method_name": method_name,
            }
        finally:
            await account.shutdown()

    return asyncio.run(_send())
