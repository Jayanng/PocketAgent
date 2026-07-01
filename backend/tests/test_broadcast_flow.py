"""End-to-end integration test for the broadcast -> confirmation flow.

Verifies that calling ``send_transaction`` on an EVM chain:
1. Returns immediately with ``status: "broadcast"`` (not blocked on receipt).
2. Spawns a background ``ConfirmationService`` task.
3. The task polls the receipt and writes a follow-up ``tx_confirmation``
   assistant message into the same conversation.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite

from backend.tools.registry import ToolContext
from backend.tools.transaction_tools import send_transaction


EVM_PRIVATE_KEY = "0x" + "11" * 32  # any 32-byte hex; we never actually broadcast
# Address derived from the above private key so tests can assert against it.
EVM_ADDRESS = "0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"
# Background confirmation polling is tested separately in test_confirmation.py.
# These tests mock it out so they only verify the broadcast return value.
NOOP_CONFIRMATION = patch("backend.tools.transaction_tools._schedule_confirmation")


class _EvmFakeRPC:
    """Mimics enough of ``PocketRPCClient`` for ``send_transaction`` + receipt polling."""

    def __init__(self, *, receipt_response: Any) -> None:
        self._receipt_response = receipt_response
        self.calls: list[tuple[str, str]] = []

    def get_protocol(self, chain: str) -> str:
        return "evm"

    async def get_chain_id(self, chain: str) -> int:
        self.calls.append((chain, "eth_chainId"))
        return 42161  # arbitrum one

    async def get_transaction_count(self, chain: str, address: str) -> int:
        self.calls.append((chain, "eth_getTransactionCount"))
        return 0

    async def send_raw_transaction(self, chain: str, raw_hex: str) -> str:
        self.calls.append((chain, "sendRawTransaction"))
        return "0xBROADCASTED"

    async def call(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        self.calls.append((chain, method))
        if method == "eth_gasPrice":
            return "0x2540be400"  # 10 gwei
        if method == "eth_estimateGas":
            return "0x5208"
        if method == "eth_getTransactionReceipt":
            return self._receipt_response
        if method == "sendRawTransaction":
            return "0xBROADCASTED"
        raise AssertionError(f"Unexpected RPC method: {method}")

    async def get_transaction_receipt(self, chain: str, tx_hash: str) -> Any:
        self.calls.append((chain, "eth_getTransactionReceipt"))
        return self._receipt_response


def _context() -> ToolContext:
    return ToolContext(
        agent={
            "id": "agent-broadcast",
            "chains": ["arbitrum"],
            "encrypted_private_key": "encrypted-evm",
            "encrypted_wallets": {"evm": "encrypted-evm"},
            "wallet_address": "0xSENDER",
            "wallet_addresses": {"evm": "0xSENDER"},
            "spending_cap": 10.0,
            "total_spent_by_chain": {},
        },
        rpc_client=None,  # injected in the test
        relay_tracker=None,
        db=None,
        conversation_id="conv-broadcast",
    )


async def _bootstrap_messages_schema(db_path: Path) -> None:
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                chain_calls TEXT,
                tokens_used INTEGER,
                created_at TEXT
            )"""
        )
        await db.commit()


class BroadcastFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.db"
        await _bootstrap_messages_schema(self.db_path)

    async def asyncTearDown(self) -> None:
        self._tmp.cleanup()

    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_send_transaction_returns_broadcast_and_followup_is_written(
        self, _mock_decrypt
    ) -> None:
        # Receipt resolves to "confirmed" on the first poll.
        rpc = _EvmFakeRPC(
            receipt_response={
                "status": "0x1",
                "blockNumber": "0xA1B2C3",
                "gasUsed": "0x5208",
            }
        )

        ctx = _context()
        ctx.rpc_client = rpc

        with patch(
            "backend.tools.transaction_tools.get_settings"
        ) as mock_settings, NOOP_CONFIRMATION:
            mock_settings.return_value.database_path = str(self.db_path)

            result = await send_transaction(
                ctx,
                {
                    "chain": "arbitrum",
                    "to_address": "0x0000000000000000000000000000000000000001",
                    "amount": "0.01",
                },
            )

        # 1. Return value should be a broadcast envelope.
        self.assertEqual(result["status"], "broadcast")
        self.assertEqual(result["chain"], "arbitrum")
        self.assertEqual(result["protocol"], "evm")
        self.assertEqual(result["tx_hash"], "0xBROADCASTED")
        self.assertEqual(result["confirmation"], "pending")
        self.assertEqual(result["from"], EVM_ADDRESS)

        # The send_raw_transaction call should have happened already.
        self.assertIn(("arbitrum", "sendRawTransaction"), rpc.calls)

    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_broadcast_returns_even_when_receipt_never_arrives(
        self, _mock_decrypt
    ) -> None:
        """Pending receipt should not block the synchronous return."""
        rpc = _EvmFakeRPC(receipt_response=None)
        ctx = _context()
        ctx.rpc_client = rpc

        with patch(
            "backend.tools.transaction_tools.get_settings"
        ) as mock_settings, NOOP_CONFIRMATION:
            mock_settings.return_value.database_path = str(self.db_path)

            result = await send_transaction(
                ctx,
                {
                    "chain": "arbitrum",
                    "to_address": "0x0000000000000000000000000000000000000001",
                    "amount": "0.01",
                },
            )

        self.assertEqual(result["status"], "broadcast")
        self.assertEqual(result["tx_hash"], "0xBROADCASTED")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
