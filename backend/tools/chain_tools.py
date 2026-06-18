from __future__ import annotations

from typing import Any

try:
    from ..services.chain_registry import CHAIN_REGISTRY, get_chain_metadata
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
except ImportError:
    from services.chain_registry import CHAIN_REGISTRY, get_chain_metadata
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed


async def list_chains(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    protocol = args.get("protocol")
    chains = [
        {"chain": key, **metadata}
        for key, metadata in CHAIN_REGISTRY.items()
        if protocol is None or metadata["protocol"] == protocol
    ]
    return {"chains": chains, "count": len(chains)}


async def get_chain_info(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return {"chain": chain, **get_chain_metadata(chain)}


TOOLS = [
    register_tool(
        function_schema(
            "list_chains",
            "List PocketAgent-supported Pocket RPC chains, optionally filtered by protocol family.",
            {"protocol": {"type": "string", "enum": ["evm", "solana", "cosmos", "sui", "near", "tron"]}},
        ),
        "read",
        list_chains,
    ),
    register_tool(
        function_schema(
            "get_chain_info",
            "Get chain metadata including protocol, RPC URL, symbol, decimals, and explorer URL.",
            {"chain": {"type": "string", "description": "Chain name, e.g. ethereum, solana, osmosis"}},
            ["chain"],
        ),
        "read",
        get_chain_info,
    ),
]
