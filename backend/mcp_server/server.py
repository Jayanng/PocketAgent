"""PocketAgent MCP Server.

Exposes the 51 PocketAgent tools (32 read reimplemented from BlockchainQuery's
surface + 19 custom, including 6 non-EVM token transfer tools), 5 resources, and 4 prompts over MCP stdio transport, so
any MCP client (Claude Desktop, Codex) can drive Pocket Network directly.

Architecture: the MCP server is a thin adapter over the existing
backend/tools/TOOL_REGISTRY. It does NOT re-route tools — `call_tool` delegates
to `execute_tool(name, context, args)`, the same path the chat UI uses. This
keeps the tool surface identical across chat and MCP with zero routing drift.

Run:
    python -m backend.mcp_server.server
or, from the backend dir:
    python -m mcp_server.server
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiosqlite
from mcp.server import InitializationOptions, NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    AnyUrl,
    GetPromptResult,
    Prompt,
    Resource,
    TextContent,
    Tool,
)

try:
    from ..config import ensure_database_directory
    from ..database import get_agent
    from ..services.agent_auth import verify_agent_access_token
    from ..services.pocket_rpc import PocketRPCClient
    from ..services.relay_tracker import RelayTrackerService
    from ..tools import TOOL_REGISTRY, ToolContext, execute_tool
    from .prompts import get_mcp_prompt, list_mcp_prompts
    from .resources import ReadResourceContents, list_mcp_resources, read_resource_contents
    from .tools import list_mcp_tools
except ImportError:
    from config import ensure_database_directory
    from database import get_agent
    from services.agent_auth import verify_agent_access_token
    from services.pocket_rpc import PocketRPCClient
    from services.relay_tracker import RelayTrackerService
    from tools import TOOL_REGISTRY, ToolContext, execute_tool
    from .prompts import get_mcp_prompt, list_mcp_prompts
    from .resources import ReadResourceContents, list_mcp_resources, read_resource_contents
    from .tools import list_mcp_tools

logger = logging.getLogger(__name__)

PACKAGE_VERSION = "1.0.0"

# Capabilities that need an agent context. Native transfer executors use
# protocol-specific encrypted keys for signing.
_TRANSACT_CAPABILITIES = {"transact"}

# Shared service singletons (cheap to construct; hold an httpx pool + cache).
_rpc_client = PocketRPCClient()
_relay_tracker = RelayTrackerService()

server = Server("pocketagent")


def _requires_agent_access(spec: Any) -> bool:
    required = spec.schema.get("function", {}).get("parameters", {}).get("required", [])
    return spec.capability in _TRANSACT_CAPABILITIES or "agent_id" in required


async def _load_agent(agent_id: str) -> dict[str, Any]:
    """Load a full agent row (incl. encrypted_private_key) from the DB."""
    settings = _rpc_client.settings
    ensure_database_directory(settings.database_path)
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    try:
        return await get_agent(db, agent_id) or {}
    finally:
        await db.close()


async def _build_context(args: dict[str, Any]) -> ToolContext:
    """Build a ToolContext for a tool call.

    Transact tools require an agent context. Native transfer tools decrypt and
    sign with protocol-specific wallets. Read, compare, and analytics
    tools run with a minimal default context. The agent's `chains` restriction
    still applies to transact: the chain must be enabled for the agent
    (validate_chain_allowed enforces this in the executor).
    """
    agent: dict[str, Any] = {}
    agent_id = args.get("agent_id")
    if agent_id:
        agent = await _load_agent(str(agent_id))
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        if not verify_agent_access_token(agent, args.get("agent_access_token")):
            raise PermissionError("Valid agent_access_token is required for this agent.")
    return ToolContext(agent=agent, rpc_client=_rpc_client, relay_tracker=_relay_tracker, db=None)


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Expose all 51 registered tools as MCP Tool objects."""
    return list_mcp_tools()


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Route an MCP tool call to the existing TOOL_REGISTRY executor.

    All 51 tools are handled here — reads via the protocol dispatcher,
    custom (compare/transact/analytics/pokt/wallet/simulation/non-evm-token)
    via their registered executors. Transact tools require agent_id in
    arguments.
    """
    args = dict(arguments or {})
    if name not in TOOL_REGISTRY:
        return [_err(f"Unknown tool: {name}")]
    spec = TOOL_REGISTRY[name]

    # Transact tools need an agent context for chain permissions and, on EVM,
    # wallet signing.
    requires_agent_access = _requires_agent_access(spec)
    if requires_agent_access and not args.get("agent_id"):
        return [_err(
            f"Tool '{name}' requires an 'agent_id' argument to load the signing wallet. "
            "Pass the agent_id of a funded, active agent whose chains include the target chain."
        )]
    if requires_agent_access and not args.get("agent_access_token"):
        return [_err(
            f"Tool '{name}' requires an 'agent_access_token' argument to authorize the agent."
        )]

    try:
        context = await _build_context(args)
        # Strip server-only meta keys before passing args to the executor.
        if spec.capability in _TRANSACT_CAPABILITIES:
            clean_args = {
                k: v for k, v in args.items() if k not in {"agent_id", "agent_access_token"}
            }
        else:
            clean_args = {k: v for k, v in args.items() if k != "agent_access_token"}
        result = await execute_tool(name, context, clean_args)
    except ValueError as exc:
        return [_err(str(exc))]
    except PermissionError as exc:
        return [_err(str(exc))]
    except Exception as exc:  # noqa: BLE001 — surface any executor failure to the client as text
        logger.exception("MCP call_tool '%s' failed", name)
        return [_err(f"Tool '{name}' failed: {exc}")]

    body = result if isinstance(result, str) else json.dumps(result, indent=2, default=str)
    return [TextContent(type="text", text=body)]


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    return list_mcp_resources()


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
    return await read_resource_contents(str(uri), rpc=_rpc_client, tracker=_relay_tracker)


@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    return list_mcp_prompts()


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    return get_mcp_prompt(name, arguments)


def _err(message: str) -> TextContent:
    return TextContent(type="text", text=json.dumps({"error": message}, indent=2))


async def main() -> None:
    """Stdio entry point for Claude Desktop / Codex integration."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    logger.info("PocketAgent MCP server starting (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pocketagent",
                server_version=PACKAGE_VERSION,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli() -> None:
    """Sync entry point for the ``pocketagent-mcp`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
