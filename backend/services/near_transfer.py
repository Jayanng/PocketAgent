from __future__ import annotations

import asyncio
from typing import Any

NEAR_RPC_URL = "https://near.api.pocket.network"


def near_implicit_account_id(public_key_hex: str) -> str:
    clean = public_key_hex.removeprefix("ed25519:").strip()
    return clean.lower()


def execute_near_native_transfer(
    account_id: str,
    private_key: str,
    recipient_account_id: str,
    amount_yocto: int,
    rpc_addr: str = NEAR_RPC_URL,
) -> dict[str, Any]:
    if amount_yocto <= 0:
        raise ValueError("NEAR transfer amount must be positive.")

    async def _send() -> dict[str, Any]:
        from py_near.account import Account

        account = Account(account_id, private_key, rpc_addr=rpc_addr)
        try:
            await account.startup()
            result = await account.send_money(recipient_account_id, amount_yocto)
            tx_hash = getattr(getattr(result, "transaction", None), "hash", None)
            if not tx_hash and hasattr(result, "transaction_hash"):
                tx_hash = result.transaction_hash
            if not tx_hash:
                tx_hash = str(result)
            return {
                "from": account_id,
                "tx_hash": str(tx_hash),
                "amount_yocto": amount_yocto,
            }
        finally:
            await account.shutdown()

    return asyncio.run(_send())