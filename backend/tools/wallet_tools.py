from __future__ import annotations

import asyncio
from typing import Any

try:
    from .pokt_tools import OPERATION_RELAY_COUNTS
    from .registry import ToolContext, function_schema, register_tool, validate_chains_allowed
except ImportError:
    from tools.pokt_tools import OPERATION_RELAY_COUNTS
    from tools.registry import ToolContext, function_schema, register_tool, validate_chains_allowed


async def analyze_wallet(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Compositional wallet analysis.

    Chains up: native balances across chains + token discovery (ERC-20 / SPL /
    Cosmos denoms / Sui coins) + gas/fee estimate per chain + USD-weighted
    portfolio allocation + notional POKT relay cost.
    """
    address = str(args["address"])
    chains = [str(chain) for chain in args.get("chains") or context.agent.get("chains") or ["ethereum"]]
    chains = validate_chains_allowed(context, chains)
    include_tokens = bool(args.get("include_tokens", True))
    include_costs = bool(args.get("include_costs", True))

    rpc = context.rpc_client

    # Fan out native balances, token discovery, and gas estimates concurrently.
    balance_task = asyncio.create_task(rpc.multi_chain_balance(address, chains))
    token_tasks = {
        chain: asyncio.create_task(rpc.discover_tokens(chain, address))
        for chain in chains
    } if include_tokens else {}
    gas_tasks = {
        chain: asyncio.create_task(rpc.get_gas_price(chain))
        for chain in chains
    }

    balances_result = await balance_task
    tokens: dict[str, list[dict[str, Any]]] = {}
    gas_estimate: dict[str, Any] = {}
    for chain in chains:
        if token_tasks:
            try:
                tokens[chain] = await token_tasks[chain]
            except Exception as exc:
                tokens[chain] = [{"error": str(exc)}]
        try:
            gas_estimate[chain] = await gas_tasks[chain]
        except Exception as exc:
            gas_estimate[chain] = {"error": str(exc)}

    portfolio = _build_portfolio(balances_result["balances"], tokens if include_tokens else {})

    result: dict[str, Any] = {
        "address": address,
        "chains": chains,
        "balances": balances_result["balances"],
        "portfolio": portfolio,
        "gas_estimate": gas_estimate,
        "include_tokens": include_tokens,
    }
    if include_tokens:
        result["tokens"] = tokens
    if include_costs:
        relay_count = len(chains) * OPERATION_RELAY_COUNTS["read_balance"]
        result["notional_relay_cost"] = {
            "relay_count": relay_count,
            "pokt": round(relay_count * rpc.settings.notional_pokt_per_relay, 6),
            "note": "Estimated relay cost only; no user POKT is charged by the free public portal.",
        }
    return result


def _usd(value: Any) -> float:
    """Coerce a balance/token usd_value field to a float, treating None as 0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_portfolio(
    balances: dict[str, Any], tokens: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Aggregate native + token USD values into a weighted allocation."""
    holdings: dict[str, float] = {}

    for chain, balance in balances.items():
        if not isinstance(balance, dict) or "error" in balance:
            continue
        symbol = str(balance.get("symbol") or chain).upper()
        holdings[symbol] = holdings.get(symbol, 0.0) + _usd(balance.get("usd_value"))

    for chain_tokens in tokens.values():
        if not isinstance(chain_tokens, list):
            continue
        for token in chain_tokens:
            if not isinstance(token, dict) or "error" in token:
                continue
            symbol = str(token.get("symbol") or "UNKNOWN").upper()
            holdings[symbol] = holdings.get(symbol, 0.0) + _usd(token.get("usd_value"))

    total_usd = round(sum(holdings.values()), 2)
    allocation = [
        {
            "asset": asset,
            "usd": round(usd, 2),
            "percentage": round((usd / total_usd) * 100, 3) if total_usd > 0 else 0.0,
        }
        for asset, usd in sorted(holdings.items(), key=lambda item: item[1], reverse=True)
    ]
    return {"total_usd": total_usd, "allocation": allocation}


TOOLS = [
    register_tool(
        function_schema(
            "analyze_wallet",
            "Comprehensive wallet analysis: native balances across chains, token discovery (ERC-20/SPL/Cosmos denoms/Sui coins), gas/fee estimates, USD-weighted portfolio allocation, and notional POKT relay cost.",
            {
                "address": {"type": "string"},
                "chains": {"type": "array", "items": {"type": "string"}},
                "include_tokens": {"type": "boolean"},
                "include_costs": {"type": "boolean"},
            },
            ["address"],
        ),
        "read",
        analyze_wallet,
    )
]
