import json
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite
from openai import AsyncOpenAI

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


class AIAgentService:
    """Service for handling AI agent conversations with function calling."""

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
            self._openai_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.settings.openai_base_url,
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

            history = await list_messages(db, conversation_id=conversation_id, limit=50)
            messages = self._build_openai_messages(agent=agent, history=history)
            tools = self.get_tool_definitions(agent)

            first = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
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
                            "content": json.dumps(result),
                        }
                    )

                second_messages = [*messages, assistant_tool_call_message, *tool_result_messages]
                second = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=second_messages,
                )
                second_message = second.choices[0].message
                final_text = second_message.content or final_text
                if second.usage:
                    total_tokens += int(second.usage.total_tokens)

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

    def get_system_prompt(self, agent: dict[str, Any]) -> str:
        """Generate system prompt for the AI agent based on config."""
        chains = ", ".join(agent.get("chains") or [])
        capabilities = ", ".join(agent.get("capabilities") or [])
        connected_wallet = agent.get("connected_wallet_address")
        wallet_context = (
            f"\nThe user has connected this EVM wallet address: {connected_wallet}. "
            "Use this as the default address for balance and wallet-analysis tools unless the user provides another address.\n"
            if connected_wallet
            else "\nThe user has not connected an EVM wallet. Ask for an address before running balance tools that require one.\n"
        )
        return (
            "You are PocketAgent, an AI assistant that helps users interact with "
            "multiple blockchains through Pocket Network decentralized RPC.\n\n"
            f"Available chains: {chains}\n"
            f"Your capabilities: {capabilities}\n\n"
            f"{wallet_context}\n"
            "You can:\n"
            "- Check balances across multiple chains\n"
            "- Compare gas prices between chains\n"
            "- Send transactions if transact capability is enabled\n"
            "- Monitor chain health\n"
            "- Track Pocket relay usage statistics\n\n"
            "Always specify which chain(s) you queried. When user asks for balance "
            "without chain context, prefer all chains the agent has access to. "
            "Format blockchain data clearly with chain names, symbols, and USD values when available.\n\n"
            "Transaction confirmation flow: when a transaction tool returns "
            "``status: 'broadcast'`` (with a ``tx_hash``), the transaction has been "
            "submitted to the network's mempool but has not yet been included in a "
            "block. Tell the user the transaction is broadcasting and that an "
            "on-chain confirmation message will arrive in the chat automatically "
            "within ~30 seconds. Do NOT claim the transfer is complete, do NOT "
            "estimate finality yourself, and do NOT tell the user to ask again — "
            "the confirmation message is already being polled in the background. "
            "Include the ``tx_hash`` and, if present in the tool result, the "
            "block explorer URL the user can open right now to watch progress."
        )

    def get_tool_definitions(self, agent: dict[str, Any]) -> list[dict[str, Any]]:
        """Return OpenAI function definitions based on agent capabilities."""
        capabilities = set(agent.get("capabilities") or [])
        return get_tool_schemas(capabilities)

    async def close(self) -> None:
        if self._openai_client is not None:
            await self._openai_client.close()

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
    def _parse_tool_args(raw_args: str | None) -> dict[str, Any]:
        if not raw_args:
            return {}
        try:
            parsed = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid tool JSON arguments: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        return parsed

    @staticmethod
    def _normalize_tool_call(tool_name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        aliases = {
            "get_balance": "evm_get_balance",
            "multi_chain_balance": "compare_balances",
            "get_gas_price": "compare_chains",
            "get_block_number": "evm_get_block",
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
            args = {"chain": args["chain"], "block": "latest"}
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
