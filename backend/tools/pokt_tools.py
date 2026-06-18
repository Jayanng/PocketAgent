from __future__ import annotations

from typing import Any

try:
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
except ImportError:
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed


OPERATION_RELAY_COUNTS = {
    "read_balance": 1,
    "read_block": 1,
    "send_transaction": 2,
    "erc20_transfer": 4,
    "contract_call": 2,
}


async def estimate_relay_cost(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    operation = str(args["operation"])
    relay_count = OPERATION_RELAY_COUNTS.get(operation, 1)
    if args.get("multi_chain"):
        relay_count *= max(len(context.agent.get("chains") or [chain]), 1)
    pokt_per_relay = context.rpc_client.settings.notional_pokt_per_relay
    return {
        "chain": chain,
        "operation": operation,
        "relay_count": relay_count,
        "notional_pokt_per_relay": pokt_per_relay,
        "estimated_relay_cost_pokt": round(relay_count * pokt_per_relay, 6),
        "note": "Pocket public RPC costs the user zero POKT; this is a notional estimate for visibility.",
    }


TOOLS = [
    register_tool(
        function_schema(
            "estimate_relay_cost",
            "Estimate the NOTIONAL POKT relay cost of an operation before executing it.",
            {
                "chain": {"type": "string"},
                "operation": {"type": "string", "enum": ["read_balance", "read_block", "send_transaction", "erc20_transfer", "contract_call"]},
                "multi_chain": {"type": "boolean"},
            },
            ["chain", "operation"],
        ),
        "analytics",
        estimate_relay_cost,
    )
]
