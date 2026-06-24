from __future__ import annotations

from typing import Any

try:
    from ..services.chain_router import ChainRouter
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed, validate_chains_allowed
except ImportError:
    from services.chain_router import ChainRouter
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed, validate_chains_allowed


async def compare_chains(context: ToolContext, args: dict[str, Any]) -> Any:
    chains = validate_chains_allowed(context, [str(chain) for chain in args["chains"]])
    return await ChainRouter(context.rpc_client, default_chains=chains).get_chain_comparison(chains)


async def recommend_chain(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    operation_type = str(args["operation_type"])
    chains = context.agent.get("chains") or ["ethereum", "polygon", "arbitrum", "base", "optimism"]
    chains = validate_chains_allowed(context, [str(chain) for chain in chains])
    return await ChainRouter(context.rpc_client, default_chains=chains).recommend_chain(operation_type)


async def estimate_transaction_cost(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    operation_type = str(args["operation_type"])
    gas_units = {"native_transfer": 21_000, "erc20_transfer": 65_000, "contract_call": 120_000}.get(operation_type, 21_000)
    gas = await context.rpc_client.get_gas_price(chain)
    gas_price_gwei = gas.get("gas_price_gwei")
    protocol = context.rpc_client.get_protocol(chain)

    if protocol == "evm" and gas_price_gwei is not None:
        estimated_native = float(gas_price_gwei) * gas_units / 1_000_000_000
        return {
            "chain": chain,
            "protocol": protocol,
            "operation_type": operation_type,
            "gas_units": gas_units,
            "gas_price_gwei": gas_price_gwei,
            "estimated_native_fee": estimated_native,
            "gas": gas,
        }

    return {
        "chain": chain,
        "protocol": protocol,
        "operation_type": operation_type,
        "gas_units": gas_units,
        "estimated_native_fee": gas.get("estimated_native_fee"),
        "gas": gas,
    }


TOOLS = [
    register_tool(
        function_schema(
            "compare_chains",
            "Compare gas prices, block times, and health across multiple chains.",
            {"chains": {"type": "array", "items": {"type": "string"}}},
            ["chains"],
        ),
        "compare",
        compare_chains,
    ),
    register_tool(
        function_schema(
            "recommend_chain",
            "Recommend the best chain for a specific operation type based on gas price, speed, and cost.",
            {"operation_type": {"type": "string", "enum": ["native_transfer", "erc20_transfer", "contract_call", "simulate"]}},
            ["operation_type"],
        ),
        "compare",
        recommend_chain,
    ),
    register_tool(
        function_schema(
            "estimate_transaction_cost",
            "Estimate transaction cost for an operation on a specific chain before executing it.",
            {
                "chain": {"type": "string"},
                "operation_type": {"type": "string", "enum": ["native_transfer", "erc20_transfer", "contract_call"]},
                "amount": {"type": "string"},
                "from_address": {"type": "string"},
            },
            ["chain", "operation_type"],
        ),
        "compare",
        estimate_transaction_cost,
    ),
]
