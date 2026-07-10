import asyncio
import ast
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite
import httpx
from openai import AsyncOpenAI, OpenAIError

try:
    from ..config import ensure_database_directory, get_settings
    from ..database import (
        create_conversation,
        create_message,
        get_agent,
        get_conversation,
        list_messages,
    )
    from ..tools import ToolContext, execute_tool, get_tool_schemas
    from .pocket_rpc import PocketRPCClient
    from .relay_tracker import RelayTrackerService
except ImportError:
    from config import ensure_database_directory, get_settings
    from database import (
        create_conversation,
        create_message,
        get_agent,
        get_conversation,
        list_messages,
    )
    from tools import ToolContext, execute_tool, get_tool_schemas
    from services.pocket_rpc import PocketRPCClient
    from services.relay_tracker import RelayTrackerService

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Anti-hallucination: keyword heuristic for forcing tool_choice="required"
# -------------------------------------------------------------------------
# When the user message contains enough blockchain-query keywords (or an
# on-chain address), the first LLM call uses tool_choice="required" so the
# model cannot skip tools and answer from its pre-training data. Casual
# conversation ("hello", "what can you do?") still uses "auto".
_ONCHAIN_TRIGGER_KEYWORDS: frozenset[str] = frozenset({
    "balance", "balances", "send", "transfer", "transaction", "transactions", "tx",
    "gas", "block", "blocks", "wallet", "analyze",
    "portfolio", "token", "tokens", "contract", "swap", "stake", "staking",
    "broadcast", "receipt", "nonce", "estimate", "compare", "recommend",
    "cheapest", "cost", "costs", "relay", "relays", "stats", "analytics",
    "breakdown", "history", "holdings", "asset", "assets", "allocation",
    "deploy", "mint", "nft", "approve", "allowance", "bridge",
    "signed", "sign", "decimals", "confirm", "confirmed", "blockchain",
    "network", "state", "tps", "throughput", "finality", "latency",
    "validator", "validators", "proposer", "consensus", "throughput",
    "execution", "reverted", "revert", "pending", "queued", "mempool",
    "pool", "liquidity", "yield", "farm", "farming", "apr", "apy",
    "cheap",
})

# ── Address / identifier patterns (multi-chain) ─────────────────────────
# Used by the heuristic to detect when a user message contains an on-chain
# address and by _validate_response_grounding to audit the LLM response.
#
# Formats covered:
#   EVM address ............ 0x + 40 hex
#   EVM tx hash ............ 0x + 64 hex
#   SUI address / tx digest  0x + 64 hex
#   Solana address / sig ... base58, 43-44 chars (no 0x prefix)
#   Tron address ........... base58, T + 33 chars
#   Cosmos bech32 / NEAR ... deliberately omitted — too variable to regex
#                            reliably; guarded by numeric validation instead.
_ADDRESS_PATTERN = re.compile(
    r"0x[a-fA-F0-9]{40,64}"
    r"|[1-9A-HJ-NP-Za-km-z]{40,46}"
    r"|T[1-9A-HJ-NP-Za-km-z]{33}",
)

_HEX_ID_PATTERN = re.compile(r"0x[a-fA-F0-9]{40,64}")

# Tokenise the message into lowercased alphabetic words so keyword matching
# never double-counts sub-words (e.g. "blocks" should match "blocks" but not
# "block" when both are in the keyword set).
_WORD_PATTERN = re.compile(r"\b[a-z]+\b")

# Write-operation keywords that require an address before we force a tool
# call.  Without this guard "send tokens" would trigger tool_choice="required"
# and the LLM would be forced to fabricate parameters for send_transaction.
_WRITE_KEYWORDS: frozenset[str] = frozenset({
    "send", "transfer", "transferring", "broadcast", "swap", "swapping", "stake", "staking",
    "deploy", "deploying", "mint", "minting", "approve", "bridge", "bridging", "burn", "burning",
})

# When a message contains both write keywords AND read-action keywords
# (e.g. "recommend cheapest chain for transfer"), the user is clearly
# querying, not writing — skip the write safety guard.
_READ_ACTION_KEYWORDS: frozenset[str] = frozenset({
    "recommend", "compare", "estimate", "cheapest", "cheap", "analyze",
    "check", "stats", "analytics", "breakdown", "history",
    "cost", "costs", "gas", "balance", "balances", "portfolio",
    "holdings", "allocation", "receipt", "status",
})

# Tool names that perform writes.  Used by _resolve_tool_choice so a
# read-only agent never gets forced into ``tool_choice="required"`` when
# the user asks to send — the LLM stays on ``"auto"`` and can explain the
# capability gap instead of calling a random read tool.
_WRITE_TOOL_NAMES: frozenset[str] = frozenset({
    "send_transaction", "send_erc20", "contract_call",
})


def _requires_onchain_data(message: str) -> bool:
    """Return True when the message clearly asks for live blockchain data.

    Used to switch ``tool_choice`` from ``"auto"`` to ``"required"`` so the
    model cannot hallucinate numeric answers without calling a tool.  The
    heuristic is deliberately conservative: casual conversation ("hello",
    "what can you do?", "explain gas") still uses ``"auto"``.

    Write-intent messages without an explicit on-chain address are never
    forced — the LLM stays on ``"auto"`` so it can ask for missing
    parameters instead of fabricating them.
    """
    msg_lower = message.lower()
    if _ADDRESS_PATTERN.search(message):
        return True
    words = set(_WORD_PATTERN.findall(msg_lower))
    keyword_hits = sum(1 for kw in _ONCHAIN_TRIGGER_KEYWORDS if kw in words)
    if keyword_hits < 2:
        return False
    has_write = any(kw in words for kw in _WRITE_KEYWORDS)
    if has_write:
        has_read_action = any(kw in words for kw in _READ_ACTION_KEYWORDS)
        if not has_read_action:
            return False
    return True


# -----------------------------------------------------------------------------
# Shared OpenAI client pool
# -----------------------------------------------------------------------------
# Reusing one AsyncOpenAI instance across requests keeps the underlying httpx
# connection pool warm (DNS cached, TLS session reused, sockets kept alive).
# Without this, every chat turn re-opens ~6 TCP connections to api.gmi-serving.com,
# adding 80–250 ms of TTFT on the very first stream chunk. We build it lazily
# and let the FastAPI lifespan pre-warm it so chat latency is not inflated by
# per-request client construction.
_shared_openai_client: AsyncOpenAI | None = None
_openai_client_pool_lock = asyncio.Lock()


async def ensure_openai_client_pool() -> None:
    """Eagerly build the module-shared AsyncOpenAI client used by every chat
    request. Idempotent. Called from FastAPI lifespan in main.py."""
    global _shared_openai_client
    if _shared_openai_client is not None:
        return
    async with _openai_client_pool_lock:
        if _shared_openai_client is not None:
            return
        settings = get_settings()
        # Single source of truth for API key resolution lives on AIAgentService.
        api_key = AIAgentService._provider_api_key(settings)
        if not api_key:
            logger.warning(
                "OpenAI client pool skipped: no OPENAI_API_KEY/GMI_API_KEY configured."
            )
            return
        _shared_openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.openai_base_url,
            timeout=httpx.Timeout(
                settings.openai_read_timeout,
                connect=settings.openai_connect_timeout,
            ),
            max_retries=settings.openai_max_retries,
        )
        logger.info(
            "OpenAI client pool warmed (base_url=%s read_timeout=%ss connect=%ss "
            "max_retries=%d phase_budget_ms=%d)",
            settings.openai_base_url,
            settings.openai_read_timeout,
            settings.openai_connect_timeout,
            settings.openai_max_retries,
            settings.llm_phase_budget_ms,
        )


async def close_openai_client_pool() -> None:
    """Close the module-shared AsyncOpenAI client. Called from FastAPI lifespan
    shutdown so we never leave a connection pool open on app exit."""
    global _shared_openai_client
    if _shared_openai_client is None:
        return
    client = _shared_openai_client
    _shared_openai_client = None
    await client.close()


class AIAgentService:
    """Service for handling AI agent conversations with function calling."""

    # Per-phase LLM call budget. Mirrors the OpenAI client bounds
    # (`httpx.Timeout(45.0, connect=10.0)` × `max_retries=1` = 90 s
    # ceiling). Surfaced on the `client_error` SSE event so the FE drives
    # toast copy off real elapsed/budget ratios. Hoisted to the class so
    # tests and subclasses can override without monkey-patching the
    # function source.
    PHASE_BUDGET_MS = 90_000

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.api_key = self._provider_api_key(settings)
        # The OpenAI client is built lazily on first use so that constructing an
        # AIAgentService never requires credentials. openai>=2 raises at
        # construction time when api_key is empty, which would otherwise fire
        # before the request guard rails (agent/conversation/access checks) and
        # the explicit api_key check inside chat() — masking 404/403/410 as 503.
        self._openai_client: AsyncOpenAI | None = None
        self.rpc_client = PocketRPCClient()
        self.relay_tracker = RelayTrackerService()
        self.model = settings.openai_model
        self._active_db: aiosqlite.Connection | None = None

    @property
    def openai_client(self) -> AsyncOpenAI:
        if self._openai_client is None:
            # Prefer the module-shared client (pre-warmed by the FastAPI
            # lifespan handler in main.py) so connection pooling is shared
            # across all chat turns. Fall back to per-instance construction
            # only when the shared pool wasn't initialized (tests / CLI use).
            # The fallback MUST mirror the shared client's timeout/retries so
            # tests and CLI callers see the same first-LLM budget (~90s) as
            # the deployed service.
            self._openai_client = _shared_openai_client or AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.settings.openai_base_url,
                timeout=httpx.Timeout(
                    self.settings.openai_read_timeout,
                    connect=self.settings.openai_connect_timeout,
                ),
                max_retries=self.settings.openai_max_retries,
            )
        return self._openai_client

    async def chat(
        self,
        message: str,
        agent_id: str,
        conversation_id: str | None = None,
        connected_wallet_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message through the AI agent.

        Flow:
        1. Load agent config from DB
        2. Load conversation history
        3. Call OpenAI with function definitions
        4. Execute returned function calls (if any), then call OpenAI again
        5. Save messages to DB
        6. Return response
        """
        # Tag Pocket RPC relays with this agent so scheduled-task counters
        # (and analytics) can attribute usage. Cleared in finally below.
        prev_agent_id = getattr(self.rpc_client, "active_agent_id", None)
        self.rpc_client.active_agent_id = agent_id
        try:
            return await self._chat_inner(
                message=message,
                agent_id=agent_id,
                conversation_id=conversation_id,
                connected_wallet_address=connected_wallet_address,
            )
        finally:
            self.rpc_client.active_agent_id = prev_agent_id

    async def _chat_inner(
        self,
        message: str,
        agent_id: str,
        conversation_id: str | None = None,
        connected_wallet_address: str | None = None,
    ) -> dict[str, Any]:
        async with self._connect_db() as db:
            self._active_db = db
            agent = await get_agent(db, agent_id)
            if agent is None:
                raise LookupError(f"Agent not found: {agent_id}")
            if not agent.get("is_active", True):
                raise PermissionError(f"Agent is inactive: {agent_id}")
            if connected_wallet_address:
                agent = {**agent, "connected_wallet_address": connected_wallet_address}

            if conversation_id is None:
                conversation = await create_conversation(db, agent_id=agent_id, title=message[:80])
                conversation_id = str(conversation["id"])
            else:
                conversation = await get_conversation(db, conversation_id)
                if conversation is None:
                    raise LookupError(f"Conversation not found: {conversation_id}")
                if conversation.get("agent_id") != agent_id:
                    raise PermissionError("Conversation does not belong to this agent.")
            self._active_conversation_id = conversation_id

            if not self.api_key:
                raise RuntimeError("GMI_API_KEY or OPENAI_API_KEY is not configured.")

            # Save user message first so history is durable even if model/tool step fails.
            await create_message(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=message,
                chain_calls=[],
                tokens_used=0,
            )

            history = await list_messages(db, conversation_id=conversation_id, limit=self.settings.chat_history_limit)
            messages = self._build_openai_messages(agent=agent, history=history)
            tools = self.get_tool_definitions(agent)

            first = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice=self._resolve_tool_choice(tools, message),
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
            )

            first_message = first.choices[0].message
            chain_calls: list[dict[str, Any]] = []

            final_text = first_message.content or ""
            total_tokens = int(first.usage.total_tokens) if first.usage else 0

            if first_message.tool_calls:
                assistant_tool_call_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": first_message.content or "",
                    "tool_calls": [],
                }

                tool_result_messages: list[dict[str, Any]] = []
                for tool_call in first_message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = self._parse_tool_args(tool_call.function.arguments)
                    result = await self._execute_tool_call(
                        agent=agent,
                        tool_name=fn_name,
                        args=fn_args,
                    )
                    chain_calls.append({"tool": fn_name, "args": fn_args, "result": result})

                    assistant_tool_call_message["tool_calls"].append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": fn_name,
                                "arguments": tool_call.function.arguments or "{}",
                            },
                        }
                    )
                    tool_result_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": fn_name,
                            "content": self._serialize_tool_result(result),
                        }
                    )

                second_messages = [
                    *messages,
                    assistant_tool_call_message,
                    *tool_result_messages,
                    {
                        "role": "user",
                        "content": (
                            "Synthesize a concise answer using ONLY the data returned by the tools above. "
                            "Do not invent any numbers, addresses, hashes, or statuses. "
                            "If a tool returned an error, report it — do not guess."
                        ),
                    },
                ]
                second = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=second_messages,
                    temperature=self.settings.openai_temperature,
                    max_tokens=self.settings.openai_max_tokens,
                )
                second_message = second.choices[0].message
                final_text = second_message.content or final_text
                if second.usage:
                    total_tokens += int(second.usage.total_tokens)

                warning = self._validate_response(
                    final_text, chain_calls, user_message=message
                )
                if warning:
                    final_text = f"{final_text}\n\n{warning}"

            assistant_row = await create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=final_text,
                chain_calls=chain_calls,
                tokens_used=total_tokens,
            )

            return {
                "conversation_id": conversation_id,
                "message": assistant_row,
            }

    async def stream_chat(
        self,
        message: str,
        agent_id: str,
        conversation_id: str | None = None,
        connected_wallet_address: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming version of `chat()`.

        Yields SSE-shaped dicts in this exact order:
          {"event": "start",            "conversation_id": str}
          {"event": "text_delta",       "text": str}
          {"event": "tool_calls_start", "count": int}            (only if the model emitted tools)
          {"event": "tool_call",        "id": str, "name": str, "args": dict}
          {"event": "tool_result",      "id": str, "name": str, "result": Any}
          {"event": "final",            "conversation_id": str, "message": <db row>, "tokens_used": int, "timing": {...}}

        Errors surface as {"event": "error", "code": str, "detail": str, ...} before the
        generator returns; the FastAPI StreamingResponse wrapper emits them as-is.

        Timing instrumentation: captures per-phase latency (TTFT, RPC total,
        LLM total) on every success path AND every early-return error path so
        `fly logs | grep chat_timing` always shows the gap.
        """
        # Timing state lives at outer scope so the `finally` block can still
        # emit a partial timing line on early-return error paths.
        t_start = time.perf_counter()
        t_ttft: float | None = None
        t_first_llm_done: float | None = None
        t_rpc_start: float | None = None
        t_rpc_end: float | None = None
        t_second_llm_done: float | None = None
        tool_started_at: list[float] = []
        ordered: list[dict[str, Any]] = []
        timing_emitted = False
        # Reason tag for the chat_timing_partial fallback log line. Tracking
        # it explicitly (instead of always writing 'early_return') lets
        # operators grep client-side failures separately from fast-fail paths
        # like agent_not_found or bad_tool_args.
        early_return_reason: str = "early_return"

        # Tag Pocket RPC relays with this agent for the duration of the stream.
        prev_agent_id = getattr(self.rpc_client, "active_agent_id", None)
        self.rpc_client.active_agent_id = agent_id

        def emit_client_error(phase: str, exc: BaseException) -> dict[str, Any]:
            """Build the SSE payload we emit when an OpenAI stream fails.

            Captured elapsed_ms is measured from `t_start` (request entry),
            not from the start of the failing stream -- it's the user-visible
            'how long have I been waiting' number. `timing` is the full
            per-phase dict up to the failure point, so the FE can render a
            useful timeline if it wants to.
            """
            nonlocal early_return_reason
            now = time.perf_counter()
            elapsed_ms = max(0, round((now - t_start) * 1000))
            if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
                code = "llm_timeout"
            elif isinstance(exc, OpenAIError):
                # Connection / DNS / TLS / 5xx / etc.
                code = "llm_unavailable"
            else:
                code = "llm_error"
            early_return_reason = "client_error"
            logger.warning(
                "chat_client_error agent=%s phase=%s code=%s elapsed_ms=%d budget_ms=%d detail=%s",
                agent_id,
                phase,
                code,
                elapsed_ms,
                self.settings.llm_phase_budget_ms,
                str(exc)[:300],
            )
            return {
                "event": "client_error",
                "code": code,
                "phase": phase,
                "detail": str(exc)[:512],
                "elapsed_ms": elapsed_ms,
                "phase_budget_ms": self.settings.llm_phase_budget_ms,
                "timing": self._build_timing_dict(
                    t_start=t_start,
                    t_ttft=t_ttft,
                    t_first_llm_done=t_first_llm_done,
                    t_rpc_start=t_rpc_start,
                    t_rpc_end=t_rpc_end,
                    t_second_llm_done=t_second_llm_done,
                    tools=ordered,
                    t_end=now,
                ),
            }

        try:
            async with self._connect_db() as db:
                self._active_db = db
                agent = await get_agent(db, agent_id)
                if agent is None:
                    yield {"event": "error", "code": "agent_not_found", "detail": f"Agent not found: {agent_id}"}
                    return
                if not agent.get("is_active", True):
                    yield {"event": "error", "code": "agent_inactive", "detail": f"Agent is inactive: {agent_id}"}
                    return
                if connected_wallet_address:
                    agent = {**agent, "connected_wallet_address": connected_wallet_address}

                if conversation_id is None:
                    conversation = await create_conversation(db, agent_id=agent_id, title=message[:80])
                    conversation_id = str(conversation["id"])
                else:
                    conversation = await get_conversation(db, conversation_id)
                    if conversation is None:
                        yield {"event": "error", "code": "conversation_not_found", "detail": f"Conversation not found: {conversation_id}"}
                        return
                    if conversation.get("agent_id") != agent_id:
                        yield {"event": "error", "code": "wrong_agent", "detail": "Conversation does not belong to this agent."}
                        return
                self._active_conversation_id = conversation_id

                if not self.api_key:
                    yield {"event": "error", "code": "no_api_key", "detail": "GMI_API_KEY or OPENAI_API_KEY is not configured."}
                    return

                yield {"event": "start", "conversation_id": conversation_id}

                await create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message,
                    chain_calls=[],
                    tokens_used=0,
                )

                history = await list_messages(
                    db, conversation_id=conversation_id, limit=self.settings.chat_history_limit
                )
                messages = self._build_openai_messages(agent=agent, history=history)
                tools = self.get_tool_definitions(agent)
                logger.info(
                    "chat_tools agent=%s tool_count=%d chains=%d",
                    agent_id,
                    len(tools),
                    len(agent.get("chains") or []),
                )

                # ---------- First LLM stream ----------
                accumulated_text = ""
                accumulated_tool_calls: dict[int, dict[str, Any]] = {}
                total_tokens = 0
                try:
                    async for evt in self._stream_completion(
                        messages=messages, tools=tools,
                        tool_choice=self._resolve_tool_choice(tools, message),
                    ):
                        kind = evt["kind"]
                        if kind == "delta":
                            if t_ttft is None:
                                t_ttft = time.perf_counter()
                            accumulated_text += evt["text"]
                            yield {"event": "text_delta", "text": evt["text"]}
                        elif kind == "tool_call_delta":
                            idx = int(evt["index"])
                            slot = accumulated_tool_calls.setdefault(
                                idx, {"id": "", "name": "", "arguments": ""}
                            )
                            if evt.get("id"):
                                slot["id"] = evt["id"]
                            if evt.get("name"):
                                slot["name"] = evt["name"]
                            if evt.get("arguments"):
                                slot["arguments"] += evt["arguments"]
                        elif kind == "usage":
                            total_tokens += int(evt.get("total_tokens", 0))
                except (OpenAIError, httpx.HTTPError, asyncio.TimeoutError) as exc:
                    # Surface a client_error SSE frame so the FE can drive
                    # latency-budget-aware toast copy ("Crunching your
                    # request…" → "Retrying internally…" → "Send another
                    # message…") instead of leaving the user staring at a
                    # blank spinner for the full 90s LLM ceiling.
                    yield emit_client_error("first_llm", exc)
                    return
                t_first_llm_done = time.perf_counter()

                # ---------- Parallel tool execution ----------
                chain_calls: list[dict[str, Any]] = []
                if accumulated_tool_calls:
                    yield {"event": "tool_calls_start", "count": len(accumulated_tool_calls)}

                    tasks: list[asyncio.Task[Any]] = []
                    for idx in sorted(accumulated_tool_calls.keys()):
                        tc = accumulated_tool_calls[idx]
                        try:
                            fn_args = self._parse_tool_args(tc["arguments"] or "{}")
                        except ValueError as exc:
                            yield {
                                "event": "error",
                                "code": "bad_tool_args",
                                "tool": tc.get("name"),
                                "detail": str(exc),
                            }
                            return
                        meta = {
                            "id": tc["id"],
                            "name": tc["name"],
                            "args": fn_args,
                            "raw_arguments": tc["arguments"] or "{}",
                        }
                        ordered.append(meta)
                        yield {"event": "tool_call", "id": meta["id"], "name": meta["name"], "args": fn_args}
                        tool_started_at.append(time.perf_counter())
                        tasks.append(
                            asyncio.create_task(
                                self._execute_tool_call(agent=agent, tool_name=meta["name"], args=dict(fn_args))
                            )
                        )

                    t_rpc_start = time.perf_counter()  # start of the gather, after tasks scheduled

                    # Stream-aware gather: yield `_keepalive` markers every ~12s of
                    # silence so the SSE proxy (Fly: ~60s idle cutoff) does not cut
                    # the connection during slow tool batches (Tron ~25s, multi-chain
                    # EVM ~10–15s). The routers layer translates `_keepalive` into a
                    # `: keepalive\n\n` SSE comment — ignored by EventSource/fetch
                    # consumers but flushed by browsers to keep proxies happy.
                    raw_results: list[Any] = [None] * len(tasks)
                    remaining = set(tasks)
                    while remaining:
                        done, remaining = await asyncio.wait(
                            remaining, timeout=12.0, return_when=asyncio.FIRST_COMPLETED
                        )
                        if not done:
                            yield {"event": "_keepalive"}
                            continue
                        for finished in done:
                            idx = tasks.index(finished)
                            ordered[idx]["duration_ms"] = int(
                                (time.perf_counter() - tool_started_at[idx]) * 1000
                            )
                            exc = finished.exception()
                            raw_results[idx] = exc if exc is not None else finished.result()
                    t_rpc_end = time.perf_counter()

                    assistant_tool_call_message: dict[str, Any] = {
                        "role": "assistant",
                        "content": accumulated_text,
                        "tool_calls": [],
                    }
                    tool_result_messages: list[dict[str, Any]] = []
                    for meta, result in zip(ordered, raw_results, strict=True):
                        fn_name = meta["name"]
                        if isinstance(result, Exception):
                            result = {
                                "available": False,
                                "error": f"{type(result).__name__}: {result}",
                                "tool": fn_name,
                            }
                        chain_calls.append({"tool": fn_name, "args": meta["args"], "result": result})
                        yield {"event": "tool_result", "id": meta["id"], "name": fn_name, "result": result}
                        assistant_tool_call_message["tool_calls"].append(
                            {
                                "id": meta["id"],
                                "type": "function",
                                "function": {"name": fn_name, "arguments": meta["raw_arguments"]},
                            }
                        )
                        tool_result_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": meta["id"],
                                "name": fn_name,
                                "content": self._serialize_tool_result(result),
                            }
                        )

                    # ---------- Second LLM stream with tool results ----------
                    second_messages = [
                        *messages,
                        assistant_tool_call_message,
                        *tool_result_messages,
                        {
                            "role": "user",
                            "content": (
                                "Synthesize a concise answer using ONLY the data returned by the tools above. "
                                "Do not invent any numbers, addresses, hashes, or statuses. "
                                "If a tool returned an error, report it — do not guess."
                            ),
                        },
                    ]
                    try:
                        async for evt in self._stream_completion(messages=second_messages, tools=None):
                            kind = evt["kind"]
                            if kind == "delta":
                                if t_ttft is None:
                                    t_ttft = time.perf_counter()
                                accumulated_text += evt["text"]
                                yield {"event": "text_delta", "text": evt["text"]}
                            elif kind == "usage":
                                total_tokens += int(evt.get("total_tokens", 0))
                    except (OpenAIError, httpx.HTTPError, asyncio.TimeoutError) as exc:
                        yield emit_client_error("second_llm", exc)
                        return
                    t_second_llm_done = time.perf_counter()

                timing = self._build_timing_dict(
                    t_start=t_start,
                    t_ttft=t_ttft,
                    t_first_llm_done=t_first_llm_done,
                    t_rpc_start=t_rpc_start,
                    t_rpc_end=t_rpc_end,
                    t_second_llm_done=t_second_llm_done,
                    tools=ordered,
                    t_end=time.perf_counter(),
                )
                # Uniform integer units (-1 = phase did not run) so log scrapers
                # can rely on a stable schema.
                logger.info(
                    "chat_timing agent=%s ttft=%dms first_llm=%dms rpc=%dms "
                    "second_llm=%dms llm_total=%dms total=%dms tools=%s",
                    agent_id,
                    timing["ttft_ms"] if timing["ttft_ms"] is not None else -1,
                    timing["first_llm_ms"] if timing["first_llm_ms"] is not None else -1,
                    timing["rpc_ms"],
                    timing["second_llm_ms"],
                    timing["llm_total_ms"],
                    timing["total_ms"],
                    ",".join(f"{t['tool']}={t['duration_ms']}ms" for t in timing["tools"]) or "none",
                )

                warning = self._validate_response(
                    accumulated_text, chain_calls, user_message=message
                )
                if warning:
                    accumulated_text = f"{accumulated_text}\n\n{warning}"
                    yield {"event": "text_delta", "text": f"\n\n{warning}"}

                assistant_row = await create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=accumulated_text,
                    chain_calls=chain_calls,
                    tokens_used=total_tokens,
                )

                yield {
                    "event": "final",
                    "conversation_id": conversation_id,
                    "message": dict(assistant_row) if not isinstance(assistant_row, dict) else assistant_row,
                    "tokens_used": total_tokens,
                    "timing": timing,
                }
                timing_emitted = True
        except (GeneratorExit, asyncio.CancelledError):
            # Client disconnected mid-stream; let uvicorn close the response.
            raise
        finally:
            self.rpc_client.active_agent_id = prev_agent_id
            # Fallback log so `chat_timing` always lands in fly logs, even
            # when an early-return path (agent_not_found / bad_tool_args /
            # no_api_key / etc.) skips the success-path emit. We log at
            # WARNING level with a `reason=early_return` tag so operators can
            # grep errored turns separately from clean ones.
            if not timing_emitted:
                try:
                    timing = self._build_timing_dict(
                        t_start=t_start,
                        t_ttft=t_ttft,
                        t_first_llm_done=t_first_llm_done,
                        t_rpc_start=t_rpc_start,
                        t_rpc_end=t_rpc_end,
                        t_second_llm_done=t_second_llm_done,
                        tools=ordered,
                        t_end=time.perf_counter(),
                    )
                    logger.warning(
                        "chat_timing_partial agent=%s ttft=%dms first_llm=%dms rpc=%dms "
                        "second_llm=%dms llm_total=%dms total=%dms tools=%s reason=%s",
                        agent_id,
                        timing["ttft_ms"] if timing["ttft_ms"] is not None else -1,
                        timing["first_llm_ms"] if timing["first_llm_ms"] is not None else -1,
                        timing["rpc_ms"],
                        timing["second_llm_ms"],
                        timing["llm_total_ms"],
                        timing["total_ms"],
                        ",".join(f"{t['tool']}={t['duration_ms']}ms" for t in timing["tools"]) or "none",
                        early_return_reason,
                    )
                except Exception:
                    # Never block generator cleanup on logging hiccups.
                    pass

    async def _stream_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Wrap the OpenAI stream-completions API as a typed internal event stream.

        Yields dicts of shape:
          {"kind": "delta", "text": str}
          {"kind": "tool_call_delta", "index": int, "id"?, "name"?, "arguments"?}
          {"kind": "usage", "total_tokens": int}
        """
        client = self.openai_client
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice=tool_choice,
            temperature=self.settings.openai_temperature,
            max_tokens=self.settings.openai_max_tokens,
            stream=True,
        )
        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield {"kind": "delta", "text": delta.content}
                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        yield {
                            "kind": "tool_call_delta",
                            "index": int(tc_delta.index),
                            "id": tc_delta.id,
                            "name": tc_delta.function.name if tc_delta.function else None,
                            "arguments": tc_delta.function.arguments if tc_delta.function else None,
                        }
                if chunk.usage is not None:
                    yield {"kind": "usage", "total_tokens": int(chunk.usage.total_tokens or 0)}
        finally:
            await stream.close()

    def get_system_prompt(self, agent: dict[str, Any]) -> str:
        """Tight system prompt (~500 chars body + agent context).

        Drops the verbose capability enumeration (already conveyed by the
        OpenAI tool schemas) while preserving the three mandatory safety
        rules: mainnet-only, no-hallucinated-data, broadcast-flow. Each rule
        shrinks average TTFT by ~150 ms because smaller prompts hit the
        upstream provider faster."""
        chains = ", ".join(agent.get("chains") or []) or "(none configured)"
        capabilities = ", ".join(agent.get("capabilities") or []) or "read-only"
        connected_wallet = agent.get("connected_wallet_address")
        wallet_context = (
            f"\nConnected EVM wallet: {connected_wallet}. Use as default address for balance/analysis tools unless the user overrides.\n"
            if connected_wallet
            else "\nNo EVM wallet connected. Ask for an address before running balance/analysis tools.\n"
        )
        return (
            "You are PocketAgent — mainnet multi-chain assistant backed by Pocket Network RPC.\n"
            f"Chains: {chains} (all mainnet). Capabilities: {capabilities}.{wallet_context}\n"
            "MANDATORY RULES — no exceptions:\n"
            "1. MAINNET ONLY — never reference data from sepolia/goerli/holesky/devnet/etc.; if the user asks about a testnet, explain mainnet-only and offer the corresponding mainnet chain.\n"
            "2. NO HALLUCINATED DATA — call a tool for every live metric (balances, gas, blocks, fees, tx status). Never quote a numeric value unless it came from a tool result in THIS conversation. If an address is missing, ask.\n"
            "3. BROADCAST handling — when a tx tool returns status='broadcast' with a tx_hash, tell the user it's broadcasting and an auto-confirmation will arrive in ~30s. Always include the tx_hash and (if present) the block-explorer URL. NEVER claim completion, NEVER estimate finality, NEVER tell the user to ask again.\n"
            "4. Be concise — lead with the answer, short paragraphs or bullets, no filler.\n"
            "5. GROUNDING — when synthesizing a response from tool results, include ONLY data explicitly present in those results. Never invent numbers, addresses, tx hashes, statuses, chain metadata, or explorer URLs that did not come from a tool result. If a tool returns an error or unavailable status, report that error honestly — do not guess. If results are incomplete or a required parameter is missing, ask the user for clarification instead of fabricating.\n"
        )

    def get_tool_definitions(self, agent: dict[str, Any]) -> list[dict[str, Any]]:
        """Return OpenAI function definitions based on agent capabilities."""
        capabilities = set(agent.get("capabilities") or [])
        chains = agent.get("chains") or []
        return get_tool_schemas(capabilities, agent_chains=list(chains) if chains else None)

    @staticmethod
    def _resolve_tool_choice(tools: list[dict[str, Any]] | None, user_message: str) -> str | None:
        """Pick the OpenAI ``tool_choice`` value for the first LLM call.

        Returns ``"required"`` when the user message clearly asks for live
        blockchain data AND at least one tool is registered for this agent.
        Casual conversation / help prompts still use ``"auto"`` so the model
        can respond without forcing a spurious tool call.

        Write-intent messages (send, transfer, …) are downgraded to
        ``"auto"`` when the agent lacks transact-capable tools, so the LLM
        can explain the capability gap instead of being forced to call an
        unrelated read tool.
        """
        if not tools:
            return None
        if not _requires_onchain_data(user_message):
            return "auto"
        # If the user is asking to write but no write tools are available,
        # keep "auto" so the LLM explains the limitation instead of calling
        # a random read tool and fabricating a "sent" response.
        msg_lower = user_message.lower()
        has_write = any(
            re.search(r"\b" + re.escape(kw), msg_lower)
            for kw in _WRITE_KEYWORDS
        )
        if has_write:
            available_names = {
                t.get("function", {}).get("name", "")
                for t in tools
            }
            if not (_WRITE_TOOL_NAMES & available_names):
                return "auto"
        return "required"

    async def close(self) -> None:
        # Only close the client when this service instance owns it. If the
        # client was provided by the module-shared pool (pre-warmed via the
        # FastAPI lifespan), the pool itself is responsible for cleanup at
        # app shutdown via close_openai_client_pool().
        if self._openai_client is not None and _shared_openai_client is None:
            await self._openai_client.close()
        self._openai_client = None

    @staticmethod
    def _provider_api_key(settings: Any) -> str:
        if "gmi-serving.com" in settings.openai_base_url.lower():
            return settings.gmi_api_key or settings.openai_api_key
        return settings.openai_api_key or settings.gmi_api_key

    async def _execute_tool_call(self, agent: dict[str, Any], tool_name: str, args: dict[str, Any]) -> Any:
        args = self._inject_connected_wallet(agent, tool_name, args)
        tool_name, args = self._normalize_tool_call(tool_name, args)
        context = ToolContext(
            agent=agent,
            rpc_client=self.rpc_client,
            relay_tracker=self.relay_tracker,
            db=getattr(self, "_active_db", None),
            conversation_id=getattr(self, "_active_conversation_id", None),
        )
        return await execute_tool(tool_name, context, args)

    @staticmethod
    def _validate_response_grounding(
        response_text: str,
        chain_calls: list[dict[str, Any]],
        user_message: str = "",
    ) -> str | None:
        """Cross-check the LLM response for fabricated on-chain identifiers.

        Returns a short warning string if the response contains ``0x…`` hex
        identifiers (addresses, tx hashes) that never appeared in any tool
        result *or* the user's original message.  Returns ``None`` when the
        response is clean.

        This is a structural safety net, not a numeric audit — it catches
        the most dangerous hallucination (invented addresses / tx hashes)
        without triggering false positives on rounded or derived amounts.
        """
        if not chain_calls:
            return None
        # Collect every 0x… identifier known to this turn.
        allowed_ids: set[str] = set(_HEX_ID_PATTERN.findall(user_message))
        for call in chain_calls:
            args_str = json.dumps(call.get("args", {}))
            result_str = json.dumps(call.get("result", {}))
            allowed_ids.update(_HEX_ID_PATTERN.findall(args_str))
            allowed_ids.update(_HEX_ID_PATTERN.findall(result_str))
        # Identifiers in the LLM response that were never seen before.
        response_ids = set(_HEX_ID_PATTERN.findall(response_text))
        fabricated = response_ids - allowed_ids
        if not fabricated:
            return None
        logger.warning(
            "response_grounding_fail count=%d ids=%s",
            len(fabricated),
            ", ".join(sorted(fabricated)[:5]),
        )
        return (
            "[Note: some referenced identifiers could not be verified "
            "against tool results and may be inaccurate.]"
        )

    # ── numeric cross-validation ──────────────────────────────────────────
    # Matches decimal numbers that look like meaningful amounts (balances,
    # gas prices, block heights, USD values).  Excludes hex, dates, and
    # single-digit counts.
    _AMOUNT_PATTERN = re.compile(
        r"(?<![0-9a-fA-Fx#])(\d[\d,._]*\d)(?![0-9a-fA-F/\-])",
    )

    # Words / suffixes that, when adjacent to a number, indicate the number
    # is NOT a blockchain amount (e.g. "30 seconds", "5 attempts", "2nd").
    _NON_AMOUNT_CONTEXT = re.compile(
        r"(second|minute|hour|day|week|month|year|"
        r"times?|steps?|retries?|attempts?|retry|"
        r"\dst\b|\dnd\b|\drd\b|\dth\b|"   # ordinal: 1st, 2nd, 3rd, 4th
        r"confirmations?|"
        r"blocks?\b|"
        r"tokens?\b)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _validate_response_numbers(
        response_text: str,
        chain_calls: list[dict[str, Any]],
    ) -> str | None:
        """Check whether numeric values in the LLM response are traceable to
        tool results.

        Returns a warning string when the response contains meaningful
        numbers that cannot be matched (exactly, rounded, or within a 3 %
        relative tolerance) to any value returned by the tools.  Small
        integers (≤ 10), hex identifiers, percentages, and time/ordinal
        values are deliberately excluded to avoid false positives on
        derived counts and boilerplate text.
        """
        if not chain_calls:
            return None

        # ── collect knowable numbers from tool args + results ──────────
        tool_numbers: set[float] = set()
        for call in chain_calls:
            for field in ("args", "result"):
                raw = json.dumps(call.get(field, {}))
                for m in AIAgentService._AMOUNT_PATTERN.finditer(raw):
                    try:
                        tool_numbers.add(
                            float(m.group(1).replace(",", "").replace("_", ""))
                        )
                    except ValueError:
                        pass

        if not tool_numbers:
            return None

        # Pre-compute rounded versions so we can match "1.23" ↔ "1.234567".
        rounded_tool: set[float] = {round(v, 2) for v in tool_numbers}
        rounded_tool.update({round(v, 1) for v in tool_numbers})
        rounded_tool.update({round(v, 0) for v in tool_numbers})

        # ── scan the response ──────────────────────────────────────────
        suspicious: list[tuple[float, str]] = []
        for m in AIAgentService._AMOUNT_PATTERN.finditer(response_text):
            raw_num = m.group(1)
            try:
                val = float(raw_num.replace(",", "").replace("_", ""))
            except ValueError:
                continue
            if val <= 10:
                continue
            ctx_start = max(0, m.start() - 40)
            ctx_end = min(len(response_text), m.end() + 40)
            ctx = response_text[ctx_start:ctx_end]
            if AIAgentService._NON_AMOUNT_CONTEXT.search(ctx):
                continue
            # Match against tool numbers with progressive tolerance.
            matched = False
            for tv in tool_numbers:
                if tv == 0:
                    continue
                rel_diff = abs(val - tv) / max(abs(tv), 1e-12)
                if rel_diff < 0.03:          # 3 % relative tolerance
                    matched = True
                    break
            if not matched and round(val, 0) in rounded_tool:
                matched = True
            if not matched and round(val, 1) in rounded_tool:
                matched = True
            if not matched and round(val, 2) in rounded_tool:
                matched = True
            if not matched:
                suspicious.append((val, raw_num))

        if not suspicious:
            return None

        logger.warning(
            "response_number_validation_fail count=%d values=%s",
            len(suspicious),
            [raw for _, raw in suspicious[:10]],
        )
        return (
            "[Note: one or more numeric values in this response could not "
            "be verified against tool results and may be inaccurate.]"
        )

    # ── combined validation entry point ───────────────────────────────────
    @staticmethod
    def _validate_response(
        response_text: str,
        chain_calls: list[dict[str, Any]],
        user_message: str = "",
    ) -> str | None:
        """Run all response validation checks and return a combined warning."""
        warnings: list[str] = []
        w = AIAgentService._validate_response_grounding(
            response_text, chain_calls, user_message
        )
        if w:
            warnings.append(w)
        w = AIAgentService._validate_response_numbers(response_text, chain_calls)
        if w:
            warnings.append(w)
        return "\n".join(warnings) if warnings else None

    @staticmethod
    def _build_timing_dict(
        *,
        t_start: float,
        t_ttft: float | None,
        t_first_llm_done: float | None,
        t_rpc_start: float | None,
        t_rpc_end: float | None,
        t_second_llm_done: float | None,
        tools: list[dict[str, Any]],
        t_end: float,
    ) -> dict[str, Any]:
        """Per-phase duration dict for the chat `final` SSE event and the
        ``chat_timing`` log line.

        Every duration is a DELTA of two ``time.perf_counter()`` checkpoints,
        never an absolute timestamp scaled to ms. A previous version used a
        ``ms(t) -> int(t * 1000)`` helper on absolute perf_counter values,
        which inflated `first_llm_ms` by the entire host uptime (e.g. 1.6M
        ms after 27 min of process life) and made ``first_llm_ms > total_ms``
        on long-running workers. ``max(0, ...)`` defends against residual
        clock anomalies (NTP slew, monotonic gaps).

        Schema (all integers in milliseconds; None means the phase did not
        run; 0 means the phase ran and measured cleanly):
          ttft_ms        None | int   request entry → first text delta
          first_llm_ms   None | int   request entry → end of first stream
          rpc_ms         int          parallel tool gather (<= 0 if no tools)
          second_llm_ms  int          post-tool LLM stream (0 if no tools)
          llm_total_ms   int          first_llm + second_llm
          total_ms       int          wall-clock per turn
          tools          list[dict]   {"tool": str, "duration_ms": int}
        Invariant: ``first_llm_ms + rpc_ms + second_llm_ms <= total_ms``.
        """

        def duration_ms(
            t_end_value: float | None, t_start_value: float | None
        ) -> int | None:
            if t_end_value is None or t_start_value is None:
                return None
            # Use round() instead of int() to avoid IEEE-754 1ms jitter on
            # "clean" timestamp deltas like (4.8 - 4.0)*1000 = 799.999...
            return max(0, round((t_end_value - t_start_value) * 1000))

        first_llm_ms = duration_ms(t_first_llm_done, t_start)
        rpc_ms = duration_ms(t_rpc_end, t_rpc_start) or 0
        second_llm_ms = (
            duration_ms(
                t_second_llm_done, t_rpc_end or t_first_llm_done or t_start
            )
            or 0
        )
        return {
            "ttft_ms": duration_ms(t_ttft, t_start),
            "first_llm_ms": first_llm_ms,
            "rpc_ms": rpc_ms,
            "second_llm_ms": second_llm_ms,
            "llm_total_ms": (first_llm_ms or 0) + second_llm_ms,
            "total_ms": duration_ms(t_end, t_start) or 0,
            "tools": [
                {"tool": t["name"], "duration_ms": int(t.get("duration_ms", 0))}
                for t in tools
            ],
        }

    @staticmethod
    def _inject_connected_wallet(agent: dict[str, Any], tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if args.get("address"):
            return args
        if tool_name not in {
            "get_balance",
            "multi_chain_balance",
            "evm_get_balance",
            "compare_balances",
            "analyze_wallet",
        }:
            return args
        connected_wallet = agent.get("connected_wallet_address")
        if not connected_wallet:
            return args
        return {**args, "address": connected_wallet}

    @staticmethod
    def _serialize_tool_result(result: Any, *, max_chars: int = 12_000) -> str:
        """Keep tool payloads small enough for the follow-up LLM call."""
        serialized = json.dumps(result)
        if len(serialized) <= max_chars:
            return serialized
        if isinstance(result, dict):
            compact: dict[str, Any] = {
                "truncated": True,
                "original_size_chars": len(serialized),
                "_warning": (
                    "This result was truncated because it exceeded the size limit. "
                    "Do NOT invent or guess the missing data — only reference what is visible. "
                    "Tell the user the result was too large and share the visible portion."
                ),
            }
            for key, value in result.items():
                if isinstance(value, list):
                    compact[key] = {"count": len(value), "preview": value[:3]}
                elif isinstance(value, dict) and len(json.dumps(value)) > 2_000:
                    compact[key] = {"keys": list(value.keys())[:20], "note": "nested object omitted"}
                else:
                    compact[key] = value
            compact_json = json.dumps(compact)
            if len(compact_json) <= max_chars:
                return compact_json
        return json.dumps(
            {
                "truncated": True,
                "original_size_chars": len(serialized),
                "_warning": (
                    "This result was truncated because it exceeded the size limit. "
                    "Do NOT invent or guess the missing data. "
                    "Tell the user the result was too large and share only what is visible."
                ),
                "preview": serialized[: max_chars - 200],
            }
        )

    @staticmethod
    def _normalize_args(args: dict[str, Any]) -> dict[str, Any]:
        """Coerce Python-repr strings that smaller models emit for array/dict
        parameters (e.g. ``"['ethereum', 'polygon']"``) into real lists/dicts
        so tools receive the types they expect."""
        def _coerce(value: Any) -> Any:
            if isinstance(value, str) and len(value) >= 2 and value[0] in "[{" and value[-1] in "]}":
                try:
                    evaluated = ast.literal_eval(value)
                    if isinstance(evaluated, (list, dict)):
                        return evaluated
                except (ValueError, SyntaxError):
                    pass
            return value

        def _walk(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: _walk(_coerce(v)) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_walk(_coerce(v)) for v in obj]
            return obj

        return _walk(args)

    @staticmethod
    def _parse_tool_args(raw_args: str | None) -> dict[str, Any]:
        if not raw_args:
            return {}
        try:
            parsed = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid tool JSON arguments: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        return AIAgentService._normalize_args(parsed)

    @staticmethod
    def _normalize_tool_call(tool_name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        aliases = {
            "get_balance": "evm_get_balance",
            "multi_chain_balance": "compare_balances",
            "get_gas_price": "compare_chains",
            "get_block_number": "evm_get_block_number",
            "get_chain_id": "get_chain_info",
            "get_transaction_count": "evm_call",
            "estimate_gas": "evm_estimate_gas",
            "send_raw_transaction": "send_transaction",
            "get_transaction_receipt": "evm_get_receipt",
            "get_chain_stats": "get_cost_breakdown",
        }
        normalized = aliases.get(tool_name, tool_name)
        if tool_name == "get_gas_price":
            args = {"chains": [args["chain"]]}
        if tool_name == "get_block_number":
            args = {"chain": args["chain"]}
        if tool_name == "get_chain_id":
            args = {"chain": args["chain"]}
        if tool_name == "estimate_gas":
            args = {"chain": args["chain"], "tx": args["tx"]}
        if tool_name == "get_transaction_receipt":
            args = {"chain": args["chain"], "tx_hash": args["tx_hash"]}
        return normalized, args

    def _build_openai_messages(self, agent: dict[str, Any], history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": self.get_system_prompt(agent)}]
        for row in history:
            role = row.get("role")
            content = row.get("content", "")
            if role in {"user", "assistant"}:
                messages.append({"role": role, "content": content})
        return messages

    @asynccontextmanager
    async def _connect_db(self) -> Any:
        ensure_database_directory(self.settings.database_path)
        db = await aiosqlite.connect(self.settings.database_path)
        await db.execute("PRAGMA foreign_keys = ON;")
        db.row_factory = aiosqlite.Row
        try:
            yield db
        finally:
            self._active_db = None
            await db.close()
