from __future__ import annotations

from typing import Any

try:
    from ..database import list_relay_logs
    from .registry import ToolContext, function_schema, register_tool
except ImportError:
    from database import list_relay_logs
    from tools.registry import ToolContext, function_schema, register_tool


async def get_relay_stats(context: ToolContext, args: dict[str, Any]) -> Any:
    agent_id = str(args.get("agent_id") or context.agent["id"])
    timeframe = str(args.get("timeframe", "all"))
    return await context.relay_tracker.get_relay_stats(agent_id=agent_id, timeframe=timeframe)


async def get_relay_history(context: ToolContext, args: dict[str, Any]) -> Any:
    agent_id = str(args.get("agent_id") or context.agent["id"])
    limit = int(args.get("limit", 20))
    if context.db is None:
        return {"error": "Database context unavailable."}
    return await list_relay_logs(context.db, agent_id=agent_id, limit=limit)


async def get_cost_breakdown(context: ToolContext, args: dict[str, Any]) -> Any:
    agent_id = str(args.get("agent_id") or context.agent["id"])
    timeframe = str(args.get("timeframe", "all"))
    chain_stats = await context.relay_tracker.get_chain_stats(agent_id=agent_id, timeframe=timeframe)
    return {"agent_id": agent_id, "timeframe": timeframe, "chains": chain_stats}


TOOLS = [
    register_tool(
        function_schema(
            "get_relay_stats",
            "Get Pocket Network relay statistics: total relays, average latency, and estimated POKT costs.",
            {"agent_id": {"type": "string"}, "timeframe": {"type": "string", "enum": ["day", "week", "all"]}},
            ["agent_id"],
        ),
        "analytics",
        get_relay_stats,
    ),
    register_tool(
        function_schema(
            "get_relay_history",
            "Get recent relay log entries showing each Pocket RPC call made by an agent.",
            {"agent_id": {"type": "string"}, "limit": {"type": "integer"}},
            ["agent_id"],
        ),
        "analytics",
        get_relay_history,
    ),
    register_tool(
        function_schema(
            "get_cost_breakdown",
            "Get estimated POKT cost breakdown per chain.",
            {"agent_id": {"type": "string"}, "timeframe": {"type": "string", "enum": ["day", "week", "all"]}},
            ["agent_id"],
        ),
        "analytics",
        get_cost_breakdown,
    ),
]
