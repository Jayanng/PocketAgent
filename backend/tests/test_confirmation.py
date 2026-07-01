"""Tests for the async transaction confirmation poller.

These tests use a fake ``PocketRPCClient`` rather than a real DB or RPC so
they run as pure unit tests. They cover:

- ``ConfirmationBroker`` subscribe / publish / unsubscribe
- ``_fetch_evm``: pending -> confirmed, pending -> reverted, never confirmed
- ``_fetch_cosmos``: 200 + zero code -> confirmed, 200 + non-zero -> reverted
- ``_fetch_sui``: status "success" / "failure"
- ``_fetch_tron``: receipt.result SUCCESS / other
- ``ConfirmationService._publish_outcome``: writes a follow-up assistant
  message to the DB and publishes to the broker

The full 90s timeout path is exercised through the service with a tiny
``timeout_s`` rather than waiting in real time.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import aiosqlite

from backend.services.confirmation import (
    BROKER,
    ConfirmationBroker,
    ConfirmationOutcome,
    ConfirmationService,
    _fetch_cosmos,
    _fetch_evm,
    _fetch_sui,
    _fetch_tron,
)


class _FakeRPC:
    """Minimal stand-in for ``PocketRPCClient`` used by the fetchers."""

    def __init__(self, responses: dict[tuple[str, str], Any]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, str]] = []

    async def call(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        self.calls.append((chain, method))
        if (chain, method) in self._responses:
            response = self._responses[(chain, method)]
            if callable(response):
                return response(params)
            return response
        raise AssertionError(f"Unexpected RPC call: {chain} / {method}")

    async def get_transaction_receipt(self, chain: str, tx_hash: str) -> Any:
        self.calls.append((chain, "eth_getTransactionReceipt"))
        if (chain, "eth_getTransactionReceipt") in self._responses:
            return self._responses[(chain, "eth_getTransactionReceipt")]
        return None


# ─── Broker ─────────────────────────────────────────────────────────────────


class ConfirmationBrokerTests(unittest.IsolatedAsyncioTestCase):
    async def test_subscribe_publish_unsubscribe(self) -> None:
        broker = ConfirmationBroker()
        subscriber = await broker.subscribe("conv-1")
        await broker.publish(
            "conv-1",
            {"type": "tx_confirmation", "status": "confirmed", "tx_hash": "0xabc"},
        )
        received = await asyncio.wait_for(subscriber.queue.get(), timeout=1.0)
        self.assertEqual(received["status"], "confirmed")
        self.assertEqual(received["tx_hash"], "0xabc")

        await broker.unsubscribe(subscriber)
        # A second publish should not raise even with no subscribers.
        await broker.publish("conv-1", {"type": "tx_confirmation", "status": "reverted"})

    async def test_publish_does_not_cross_conversations(self) -> None:
        broker = ConfirmationBroker()
        sub_a = await broker.subscribe("conv-a")
        sub_b = await broker.subscribe("conv-b")
        await broker.publish("conv-a", {"type": "tx_confirmation", "status": "confirmed"})
        # Give the publish loop a tick to deliver.
        await asyncio.sleep(0)
        self.assertFalse(sub_b.queue.empty() is False and sub_b.queue.qsize() > 0)
        self.assertTrue(sub_a.queue.qsize() == 1)
        # Drain the queue so we don't leak the subscriber between tests.
        await sub_a.queue.get()
        await broker.unsubscribe(sub_a)
        await broker.unsubscribe(sub_b)


# ─── EVM fetcher ────────────────────────────────────────────────────────────


class FetchEvmTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_returns_none(self) -> None:
        rpc = _FakeRPC({("ethereum", "eth_getTransactionReceipt"): None})
        outcome = await _fetch_evm(rpc, "ethereum", "0xabc")
        self.assertIsNone(outcome)

    async def test_confirmed_returns_status(self) -> None:
        rpc = _FakeRPC(
            {
                ("ethereum", "eth_getTransactionReceipt"): {
                    "status": "0x1",
                    "blockNumber": "0x10",
                    "gasUsed": "0x5208",
                }
            }
        )
        outcome = await _fetch_evm(rpc, "ethereum", "0xabc")
        self.assertIsNotNone(outcome)
        self.assertEqual(outcome.status, "confirmed")
        self.assertEqual(outcome.block_number, 16)
        self.assertEqual(outcome.gas_used, 0x5208)

    async def test_reverted_returns_status(self) -> None:
        rpc = _FakeRPC(
            {
                ("ethereum", "eth_getTransactionReceipt"): {
                    "status": "0x0",
                    "blockNumber": "0x11",
                    "gasUsed": "0x5208",
                }
            }
        )
        outcome = await _fetch_evm(rpc, "ethereum", "0xabc")
        self.assertIsNotNone(outcome)
        self.assertEqual(outcome.status, "reverted")
        self.assertEqual(outcome.block_number, 17)


# ─── Cosmos fetcher ─────────────────────────────────────────────────────────


class FetchCosmosTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirmed(self) -> None:
        rpc = _FakeRPC(
            {
                (
                    "osmosis",
                    "/cosmos/tx/v1beta1/txs/0xHASH",
                ): {"tx_response": {"height": "12345", "code": 0}}
            }
        )
        outcome = await _fetch_cosmos(rpc, "osmosis", "0xHASH")
        self.assertEqual(outcome.status, "confirmed")
        self.assertEqual(outcome.block_number, 12345)

    async def test_reverted(self) -> None:
        rpc = _FakeRPC(
            {
                ("osmosis", "/cosmos/tx/v1beta1/txs/0xHASH"): {
                    "tx_response": {"height": "99", "code": 5, "raw_log": "insufficient funds"}
                }
            }
        )
        outcome = await _fetch_cosmos(rpc, "osmosis", "0xHASH")
        self.assertEqual(outcome.status, "reverted")
        self.assertIn("insufficient funds", outcome.error or "")


# ─── Sui fetcher ────────────────────────────────────────────────────────────


class FetchSuiTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirmed(self) -> None:
        rpc = _FakeRPC(
            {
                ("sui", "sui_getTransactionBlock"): {
                    "effects": {"status": {"status": "success"}, "checkpoint": "12345"}
                }
            }
        )
        outcome = await _fetch_sui(rpc, "sui", "DIGEST")
        self.assertEqual(outcome.status, "confirmed")
        self.assertEqual(outcome.block_number, 12345)

    async def test_failure(self) -> None:
        rpc = _FakeRPC(
            {
                ("sui", "sui_getTransactionBlock"): {
                    "effects": {"status": {"status": "failure", "error": "MoveAbort"}}
                }
            }
        )
        outcome = await _fetch_sui(rpc, "sui", "DIGEST")
        self.assertEqual(outcome.status, "reverted")
        self.assertIn("MoveAbort", outcome.error or "")


# ─── Tron fetcher ───────────────────────────────────────────────────────────


class FetchTronTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirmed(self) -> None:
        rpc = _FakeRPC(
            {
                ("tron", "wallet/gettransactioninfobyid"): {
                    "id": "0xHASH",
                    "blockNumber": 50000,
                    "receipt": {"result": "SUCCESS", "energy_usage_total": 65000},
                }
            }
        )
        outcome = await _fetch_tron(rpc, "tron", "0xHASH")
        self.assertEqual(outcome.status, "confirmed")
        self.assertEqual(outcome.block_number, 50000)
        self.assertEqual(outcome.gas_used, 65000)

    async def test_reverted(self) -> None:
        rpc = _FakeRPC(
            {
                ("tron", "wallet/gettransactioninfobyid"): {
                    "id": "0xHASH",
                    "blockNumber": 50001,
                    "receipt": {"result": "REVERT"},
                }
            }
        )
        outcome = await _fetch_tron(rpc, "tron", "0xHASH")
        self.assertEqual(outcome.status, "reverted")


# ─── ConfirmationService.publish_outcome ────────────────────────────────────


class PublishOutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def test_writes_message_and_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            # Bootstrap a minimal schema.
            async with aiosqlite.connect(str(db_path)) as db:
                await db.execute(
                    "CREATE TABLE messages (id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, chain_calls TEXT, tokens_used INTEGER, created_at TEXT)"
                )
                await db.commit()

            rpc = _FakeRPC({})
            broker = ConfirmationBroker()
            service = ConfirmationService(rpc_client=rpc, broker=broker)

            subscriber = await broker.subscribe("conv-99")

            outcome = ConfirmationOutcome(status="confirmed", block_number=42, gas_used=21000)
            await service._publish_outcome(
                chain="arbitrum",
                tx_hash="0xfeed",
                conversation_id="conv-99",
                db_path=str(db_path),
                agent_id="agent-x",
                outcome=outcome,
                tool_name="send_transaction",
                original_tool_args={"chain": "arbitrum", "amount": "0.01"},
            )

            # Verify the message landed in the DB.
            async with aiosqlite.connect(str(db_path)) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT role, content, chain_calls FROM messages") as cursor:
                    row = await cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["role"], "assistant")
            self.assertIn("Confirmed on Arbitrum One", row["content"])
            calls = json.loads(row["chain_calls"])
            self.assertEqual(calls[0]["tool"], "tx_confirmation")
            self.assertEqual(calls[0]["result"]["status"], "confirmed")
            self.assertEqual(calls[0]["result"]["block_number"], 42)
            self.assertIn("/tx/0xfeed", calls[0]["result"]["explorer_url"])

            # Verify the broker delivered the event.
            event = await asyncio.wait_for(subscriber.queue.get(), timeout=1.0)
            self.assertEqual(event["type"], "tx_confirmation")
            self.assertEqual(event["status"], "confirmed")
            self.assertIn("message", event)
            self.assertIn("Confirmed on", event["message"]["content"])

            await broker.unsubscribe(subscriber)


# ─── ConfirmationService.schedule timeout path ──────────────────────────────


class ScheduleTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_timeout_writes_pending_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            async with aiosqlite.connect(str(db_path)) as db:
                await db.execute(
                    "CREATE TABLE messages (id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, chain_calls TEXT, tokens_used INTEGER, created_at TEXT)"
                )
                await db.commit()

            # RPC always returns None -> poller never sees a receipt.
            rpc = _FakeRPC(
                {
                    ("ethereum", "eth_getTransactionReceipt"): None,
                    ("ethereum", "eth_blockNumber"): "0x1",
                }
            )
            broker = ConfirmationBroker()
            service = ConfirmationService(rpc_client=rpc, broker=broker)

            subscriber = await broker.subscribe("conv-timeout")

            # Patch _POLL_BACKOFF_SECONDS via the module so we don't wait 90s.
            from backend.services import confirmation as confirmation_mod

            original = confirmation_mod._POLL_BACKOFF_SECONDS
            confirmation_mod._POLL_BACKOFF_SECONDS = (0.01, 0.01, 0.01)
            try:
                task = service.schedule(
                    chain="ethereum",
                    tx_hash="0xstuck",
                    conversation_id="conv-timeout",
                    db_path=str(db_path),
                    agent_id="agent-y",
                    timeout_s=0.5,
                )
                await asyncio.wait_for(task, timeout=10.0)
            finally:
                confirmation_mod._POLL_BACKOFF_SECONDS = original

            async with aiosqlite.connect(str(db_path)) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT content, chain_calls FROM messages") as cursor:
                    row = await cursor.fetchone()
            self.assertIsNotNone(row, "expected a pending_timeout message in the DB")
            self.assertIn("Still pending on", row["content"])
            calls = json.loads(row["chain_calls"])
            self.assertEqual(calls[0]["result"]["status"], "pending_timeout")

            event = await asyncio.wait_for(subscriber.queue.get(), timeout=1.0)
            self.assertEqual(event["status"], "pending_timeout")
            await broker.unsubscribe(subscriber)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
