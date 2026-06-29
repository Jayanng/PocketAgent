from __future__ import annotations

from typing import Any

try:
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed, validate_chains_allowed
except ImportError:
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed, validate_chains_allowed


async def evm_get_balance(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.get_balance(chain, str(args["address"]))


async def solana_get_balance(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    validate_chain_allowed(context, "solana")
    return await context.rpc_client.get_balance("solana", str(args["address"]))


async def cosmos_get_balance(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.get_balance(chain, str(args["address"]))


async def sui_get_balance(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    validate_chain_allowed(context, "sui")
    return await context.rpc_client.get_balance("sui", str(args["address"]))


async def compare_balances(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    address = str(args["address"])
    chains = validate_chains_allowed(context, [str(chain) for chain in args["chains"]])
    return await context.rpc_client.multi_chain_balance(address, chains)


async def convert_units(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    value = str(args["value"])
    decimals = int(args.get("decimals", 18))
    direction = str(args.get("direction", "smallest_to_native"))
    if direction == "native_to_smallest":
        converted = int(float(value) * (10**decimals))
    else:
        converted = int(value) / (10**decimals)
    return {"value": value, "decimals": decimals, "direction": direction, "converted": converted}


TOOLS = [
    register_tool(
        function_schema(
            "evm_get_balance",
            "Get native token balance on an EVM chain via Pocket RPC.",
            {"chain": {"type": "string"}, "address": {"type": "string"}},
            ["chain", "address"],
        ),
        "read",
        evm_get_balance,
    ),
    register_tool(
        function_schema(
            "solana_get_balance",
            "Get SOL balance for a Solana address via Pocket RPC.",
            {"address": {"type": "string"}},
            ["address"],
        ),
        "read",
        solana_get_balance,
    ),
    register_tool(
        function_schema(
            "cosmos_get_balance",
            "Get native Cosmos-family balance for an address via Pocket REST/RPC.",
            {"chain": {"type": "string"}, "address": {"type": "string"}},
            ["chain", "address"],
        ),
        "read",
        cosmos_get_balance,
    ),
    register_tool(
        function_schema(
            "sui_get_balance",
            "Get SUI balance for an address via Pocket RPC.",
            {"address": {"type": "string"}},
            ["address"],
        ),
        "read",
        sui_get_balance,
    ),
    register_tool(
        function_schema(
            "compare_balances",
            "Compare native balances for one address across multiple chains.",
            {"address": {"type": "string"}, "chains": {"type": "array", "items": {"type": "string"}}},
            ["address", "chains"],
        ),
        "read",
        compare_balances,
    ),
    register_tool(
        function_schema(
            "convert_units",
            "Convert between smallest units and native units using token decimals.",
            {
                "value": {"type": "string"},
                "decimals": {"type": "integer"},
                "direction": {"type": "string", "enum": ["smallest_to_native", "native_to_smallest"]},
            },
            ["value"],
        ),
        "read",
        convert_units,
    ),
]
