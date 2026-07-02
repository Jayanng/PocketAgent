"""Background transaction confirmation polling.

After ``_sign_and_send_*_transaction`` broadcasts a transaction, the chat
endpoint returns immediately so the user sees a "broadcast" message without
waiting on chain finality. This service then takes over: it polls the
appropriate receipt endpoint for each protocol, and when the tx is confirmed,
reverted, or times out, it writes a follow-up assistant message into the
conversation so the chat stream picks it up via SSE.

Polling schedules are protocol-aware (faster for L1s, slower for L2s) but
share a common exponential-backoff envelope: 1s, 2s, 4s, 8s, 15s, 30s, then
30s repeatedly up to ``timeout_s`` (default 90s).

A tiny in-memory pub/sub (``ConfirmationBroker``) lets the SSE endpoint fan
out newly-arrived messages to listeners without coupling this module to
FastAPI.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import aiosqlite

try:
    from .chain_registry import get_chain_metadata
    from .pocket_rpc import PocketRPCClient
    from ..database import create_message
except ImportError:  # pragma: no cover - allow running as a script
    from services.chain_registry import get_chain_metadata
    from services.pocket_rpc import PocketRPCClient
    from database import create_message


logger = logging.getLogger(__name__)


# Polling schedule (seconds between attempts). The envelope expands from ~1s
# to ~30s and stays there. Total wall time for the default schedule:
# 1 + 2 + 4 + 8 + 15 + 30 + 30 = 90s, matching the default ``timeout_s``.
_POLL_BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 15.0, 30.0, 30.0)


# ─── Pub/Sub ────────────────────────────────────────────────────────────────


@dataclass
class _Subscriber:
    conversation_id: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)

    # Object-identity based hashing so _Subscriber can be stored in a set.
    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        return self is other


class ConfirmationBroker:
    """In-memory broker for new confirmation messages.

    Each SSE endpoint registers a subscriber for a ``conversation_id``; the
    ConfirmationService publishes a small event whenever it appends a
    confirmation message to the DB. The queue is bounded so a stalled client
    cannot leak memory.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[_Subscriber]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, conversation_id: str) -> _Subscriber:
        subscriber = _Subscriber(conversation_id=conversation_id)
        async with self._lock:
            self._subscribers.setdefault(conversation_id, set()).add(subscriber)
        return subscriber

    async def unsubscribe(self, subscriber: _Subscriber) -> None:
        async with self._lock:
            bucket = self._subscribers.get(subscriber.conversation_id)
            if bucket and subscriber in bucket:
                bucket.discard(subscriber)
                if not bucket:
                    self._subscribers.pop(subscriber.conversation_id, None)

    async def publish(self, conversation_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            bucket = list(self._subscribers.get(conversation_id, ()))
        for subscriber in bucket:
            try:
                subscriber.queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Dropping confirmation event for %s — subscriber queue full",
                    conversation_id,
                )


# Module-level singleton. Routers and the confirmation service both import
# this so they share state without DI gymnastics.
BROKER = ConfirmationBroker()


# ─── Confirmation result types ──────────────────────────────────────────────


@dataclass
class ConfirmationOutcome:
    status: str  # "confirmed" | "reverted" | "pending_timeout"
    block_number: int | None = None
    gas_used: int | None = None
    error: str | None = None
    extra: dict[str, Any] | None = None


# ─── Per-protocol receipt fetchers ──────────────────────────────────────────


def _hex_to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 16) if value.startswith("0x") else int(value)
        except ValueError:
            return None
    return None


async def _fetch_evm(
    rpc_client: PocketRPCClient,
    chain: str,
    tx_hash: str,
) -> ConfirmationOutcome | None:
    """Fetch an EVM receipt via ``eth_getTransactionReceipt``.

    Returns ``None`` while the tx is still pending, or a ``ConfirmationOutcome``
    once it has been mined (success or revert).
    """
    receipt = await rpc_client.get_transaction_receipt(chain, tx_hash)
    if receipt is None:
        return None
    # Some RPC shims wrap the standard payload in {"result": ...}.
    if isinstance(receipt, dict) and "result" in receipt and "status" not in receipt:
        receipt = receipt["result"]
    if not isinstance(receipt, dict) or not receipt.get("blockNumber"):
        return None

    status_raw = receipt.get("status")
    block_number = _hex_to_int(receipt.get("blockNumber"))
    gas_used = _hex_to_int(receipt.get("gasUsed"))

    if str(status_raw).lower() in {"0x1", "1", "true"}:
        return ConfirmationOutcome(
            status="confirmed", block_number=block_number, gas_used=gas_used
        )
    if str(status_raw).lower() in {"0x0", "0", "false"}:
        return ConfirmationOutcome(
            status="reverted",
            block_number=block_number,
            gas_used=gas_used,
            error="transaction reverted on-chain",
        )
    # Unknown status — keep polling.
    return None


async def _fetch_solana(
    rpc_client: PocketRPCClient,
    chain: str,
    tx_hash: str,
) -> ConfirmationOutcome | None:
    """Poll Solana via ``getSignatureStatuses``.

    We treat anything below ``confirmed`` as still-pending so we don't report
    success on a tx that could still be rolled back during the ``processed``
    or ``confirmed`` stages.
    """
    statuses = await rpc_client.call(
        chain,
        "getSignatureStatuses",
        [[tx_hash], {"searchTransactionHistory": True}],
    )
    value: Any = None
    if isinstance(statuses, dict):
        value = statuses.get("value")
    elif isinstance(statuses, list):
        value = statuses
    if not value:
        return None
    row = (
        value[0]
        if isinstance(value, list) and value
        else (value if isinstance(value, dict) else None)
    )
    if not row:
        return None
    confirmation = row.get("confirmation") if isinstance(row, dict) else None
    if confirmation in (None, "processed", "confirmed"):
        return None
    if row.get("err"):
        return ConfirmationOutcome(status="reverted", error=str(row["err"]))

    slot: int | None = None
    try:
        tx = await rpc_client.call(
            chain, "getTransaction", [tx_hash, {"encoding": "json"}]
        )
        if isinstance(tx, dict) and isinstance(tx.get("slot"), int):
            slot = tx["slot"]
    except Exception:
        slot = None
    return ConfirmationOutcome(
        status="confirmed",
        block_number=slot,
        extra={"confirmation": confirmation},
    )


async def _fetch_cosmos(
    rpc_client: PocketRPCClient,
    chain: str,
    tx_hash: str,
) -> ConfirmationOutcome | None:
    """Poll Cosmos tx endpoint until 200 + non-zero height."""
    try:
        result = await rpc_client.call(chain, f"/cosmos/tx/v1beta1/txs/{tx_hash}", [])
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "404" in msg or "notfound" in msg:
            return None
        logger.debug("cosmos receipt poll error for %s: %s", tx_hash, exc)
        return None
    if not isinstance(result, dict):
        return None
    tx_response = result.get("tx_response") or {}
    if not tx_response:
        return None
    height = tx_response.get("height")
    if not height or str(height) == "0":
        return None
    code = tx_response.get("code")
    block_number = _hex_to_int(height) if isinstance(height, str) else (
        int(height) if isinstance(height, int) else None
    )
    if code in (None, 0, "0"):
        return ConfirmationOutcome(status="confirmed", block_number=block_number)
    return ConfirmationOutcome(
        status="reverted",
        block_number=block_number,
        error=f"cosmos tx code={code}: {tx_response.get('raw_log', 'unknown error')}",
    )


async def _fetch_sui(
    rpc_client: PocketRPCClient,
    chain: str,
    tx_hash: str,
) -> ConfirmationOutcome | None:
    try:
        result = await rpc_client.call(
            chain, "sui_getTransactionBlock", [tx_hash, {"showEffects": True}]
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "404" in msg:
            return None
        logger.debug("sui receipt poll error for %s: %s", tx_hash, exc)
        return None
    if not isinstance(result, dict):
        return None
    effects = result.get("effects") or {}
    if not effects:
        return None
    status_obj = effects.get("status") or {}
    status_str = (
        (status_obj.get("status") or "").lower()
        if isinstance(status_obj, dict)
        else ""
    )
    checkpoint = effects.get("checkpoint") or result.get("checkpoint")
    block_number: int | None = None
    if isinstance(checkpoint, int):
        block_number = checkpoint
    elif isinstance(checkpoint, str):
        try:
            block_number = int(checkpoint)
        except ValueError:
            block_number = None
    if status_str == "success":
        return ConfirmationOutcome(status="confirmed", block_number=block_number)
    if status_str == "failure":
        return ConfirmationOutcome(
            status="reverted",
            block_number=block_number,
            error=str(status_obj.get("error", "sui tx failure")),
        )
    return None


async def _fetch_near(
    rpc_client: PocketRPCClient,
    chain: str,
    tx_hash: str,
    sender_account_id: str | None,
) -> ConfirmationOutcome | None:
    if not sender_account_id:
        logger.warning("NEAR confirmation skipped — no sender account_id available")
        return None
    try:
        result = await rpc_client.call(chain, "tx", [tx_hash, sender_account_id])
    except Exception as exc:
        msg = str(exc).lower()
        if "doesn't exist" in msg or "404" in msg:
            return None
        logger.debug("near receipt poll error for %s: %s", tx_hash, exc)
        return None
    if not isinstance(result, dict):
        return None
    block_hash = result.get("block_hash") or result.get("blockHeight")
    block_number: int | None = None
    if isinstance(block_hash, int):
        block_number = block_hash
    status = result.get("status")
    if isinstance(status, dict):
        failure = status.get("Failure") or status.get("failure")
        if failure:
            return ConfirmationOutcome(
                status="reverted", block_number=block_number, error=str(failure)
            )
    return ConfirmationOutcome(status="confirmed", block_number=block_number)


async def _fetch_tron(
    rpc_client: PocketRPCClient,
    chain: str,
    tx_hash: str,
) -> ConfirmationOutcome | None:
    try:
        info = await rpc_client.call(
            chain,
            "wallet/gettransactioninfobyid",
            [{"value": tx_hash, "visible": True}],
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "404" in msg:
            return None
        logger.debug("tron receipt poll error for %s: %s", tx_hash, exc)
        return None
    if not info or not isinstance(info, dict) or not info.get("id"):
        return None
    block_number = info.get("blockNumber")
    receipt = info.get("receipt") or {}
    result_flag = receipt.get("result") if isinstance(receipt, dict) else None
    if result_flag == "SUCCESS":
        return ConfirmationOutcome(
            status="confirmed",
            block_number=block_number,
            gas_used=receipt.get("energy_usage_total") or receipt.get("net_usage"),
        )
    if result_flag:
        return ConfirmationOutcome(
            status="reverted",
            block_number=block_number,
            error=f"tron result={result_flag}",
        )
    return None


# ─── ConfirmationService ────────────────────────────────────────────────────


class ConfirmationService:
    """Polls for tx receipts and writes a follow-up message on resolution."""

    def __init__(
        self,
        rpc_client: PocketRPCClient | None = None,
        broker: ConfirmationBroker | None = None,
    ) -> None:
        self.rpc_client = rpc_client or PocketRPCClient()
        self.broker = broker or BROKER

    def schedule(
        self,
        *,
        chain: str,
        tx_hash: str,
        conversation_id: str,
        db_path: str,
        agent_id: str | None = None,
        sender_account_id: str | None = None,
        timeout_s: float = 90.0,
        tool_name: str = "send_transaction",
        original_tool_args: dict[str, Any] | None = None,
    ) -> asyncio.Task:
        """Spawn a background polling task. Returns the task for tests/callers."""
        return asyncio.create_task(
            self._run(
                chain=chain,
                tx_hash=tx_hash,
                conversation_id=conversation_id,
                db_path=db_path,
                agent_id=agent_id,
                sender_account_id=sender_account_id,
                timeout_s=timeout_s,
                tool_name=tool_name,
                original_tool_args=original_tool_args,
            ),
            name=f"confirmation:{chain}:{tx_hash[:10]}",
        )

    async def _run(
        self,
        *,
        chain: str,
        tx_hash: str,
        conversation_id: str,
        db_path: str,
        agent_id: str | None,
        sender_account_id: str | None,
        timeout_s: float,
        tool_name: str,
        original_tool_args: dict[str, Any] | None,
    ) -> None:
        try:
            protocol = get_chain_metadata(chain)["protocol"]
        except Exception as exc:
            logger.error("confirmation: unknown chain %s: %s", chain, exc)
            return

        elapsed = 0.0
        try:
            for delay in _POLL_BACKOFF_SECONDS:
                remaining = timeout_s - elapsed
                if remaining <= 0:
                    break
                await asyncio.sleep(min(delay, remaining))
                elapsed += delay
                outcome = await self._fetch_one(protocol, chain, tx_hash, sender_account_id)
                if outcome is None:
                    continue
                await self._publish_outcome(
                    chain=chain,
                    tx_hash=tx_hash,
                    conversation_id=conversation_id,
                    db_path=db_path,
                    agent_id=agent_id,
                    outcome=outcome,
                    tool_name=tool_name,
                    original_tool_args=original_tool_args,
                )
                return
            # Timed out.
            await self._publish_outcome(
                chain=chain,
                tx_hash=tx_hash,
                conversation_id=conversation_id,
                db_path=db_path,
                agent_id=agent_id,
                outcome=ConfirmationOutcome(
                    status="pending_timeout",
                    error=f"not confirmed within {int(timeout_s)}s",
                ),
                tool_name=tool_name,
                original_tool_args=original_tool_args,
            )
        except Exception as exc:  # noqa: BLE001 - background work must never crash
            logger.exception("confirmation task crashed for %s on %s: %s", tx_hash, chain, exc)
            await self._publish_outcome(
                chain=chain,
                tx_hash=tx_hash,
                conversation_id=conversation_id,
                db_path=db_path,
                agent_id=agent_id,
                outcome=ConfirmationOutcome(
                    status="pending_timeout", error=f"poller error: {exc}"
                ),
                tool_name=tool_name,
                original_tool_args=original_tool_args,
            )

    async def _fetch_one(
        self,
        protocol: str,
        chain: str,
        tx_hash: str,
        sender_account_id: str | None,
    ) -> ConfirmationOutcome | None:
        if protocol == "evm":
            return await _fetch_evm(self.rpc_client, chain, tx_hash)
        if protocol == "solana":
            return await _fetch_solana(self.rpc_client, chain, tx_hash)
        if protocol == "cosmos":
            return await _fetch_cosmos(self.rpc_client, chain, tx_hash)
        if protocol == "sui":
            return await _fetch_sui(self.rpc_client, chain, tx_hash)
        if protocol == "near":
            return await _fetch_near(self.rpc_client, chain, tx_hash, sender_account_id)
        if protocol == "tron":
            return await _fetch_tron(self.rpc_client, chain, tx_hash)
        logger.warning("Confirmation polling: unsupported protocol %s", protocol)
        return None

    async def _publish_outcome(
        self,
        *,
        chain: str,
        tx_hash: str,
        conversation_id: str,
        db_path: str,
        agent_id: str | None,
        outcome: ConfirmationOutcome,
        tool_name: str,
        original_tool_args: dict[str, Any] | None,
    ) -> None:
        try:
            metadata = get_chain_metadata(chain)
        except Exception as exc:
            logger.error("confirmation: unknown chain %s: %s", chain, exc)
            metadata = {"name": chain, "symbol": "", "explorer_url": ""}

        explorer_base = (metadata.get("explorer_url") or "").rstrip("/")
        explorer_url = f"{explorer_base}/tx/{tx_hash}" if explorer_base else None

        chain_call = {
            "tool": "tx_confirmation",
            "args": {"chain": chain, "tx_hash": tx_hash, **(original_tool_args or {})},
            "result": {
                "status": outcome.status,
                "chain": chain,
                "tx_hash": tx_hash,
                "block_number": outcome.block_number,
                "gas_used": outcome.gas_used,
                "explorer_url": explorer_url,
                "error": outcome.error,
                **(outcome.extra or {}),
            },
        }

        content = _format_content(
            chain_name=metadata.get("name", chain),
            chain_symbol=metadata.get("symbol", ""),
            outcome=outcome,
            explorer_url=explorer_url,
        )

        try:
            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
        except Exception as exc:
            logger.error("confirmation: failed to open DB %s: %s", db_path, exc)
            return
        try:
            await create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                chain_calls=[chain_call],
                tokens_used=0,
            )
        finally:
            await db.close()

        await self.broker.publish(
            conversation_id,
            {
                "type": "tx_confirmation",
                "conversation_id": conversation_id,
                "chain": chain,
                "tx_hash": tx_hash,
                "status": outcome.status,
                "block_number": outcome.block_number,
                "gas_used": outcome.gas_used,
                "explorer_url": explorer_url,
                "agent_id": agent_id,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "chain_calls": [chain_call],
                    "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                },
            },
        )


def _format_content(
    *,
    chain_name: str,
    chain_symbol: str,
    outcome: ConfirmationOutcome,
    explorer_url: str | None,
) -> str:
    """Render a human-readable confirmation message body (Markdown)."""
    link = f"[View on explorer]({explorer_url})" if explorer_url else ""
    gas_part = ""
    if outcome.gas_used is not None and outcome.status == "confirmed":
        gas_part = f" Gas used: `{outcome.gas_used:,}`."
    block_part = ""
    if outcome.block_number is not None:
        block_part = f" Block `{outcome.block_number:,}`."
    if outcome.status == "confirmed":
        head = f"✅ **Confirmed on {chain_name}** — broadcast landed on-chain."
        return f"{head}{block_part}{gas_part} {link}".strip()
    if outcome.status == "reverted":
        err = outcome.error or "transaction reverted on-chain"
        return (
            f"❌ **Reverted on {chain_name}** — broadcast was included but the "
            f"transaction did not succeed. Reason: `{err}`.{block_part} {link}".strip()
        )
    err = outcome.error or "still pending in mempool"
    return (
        f"⏳ **Still pending on {chain_name}** after the polling window "
        f"({err}). It may confirm shortly; check the explorer for live status. "
        f"{link}".strip()
    )
