"""MCP Prompts — pre-built prompt templates an MCP client can invoke.

Prompts are reusable instructions that scaffold common multi-chain tasks.
BlockchainQuery has no prompts — these are a PocketAgent addition.
"""

from __future__ import annotations

from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent


def list_mcp_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="analyze_wallet",
            description="Analyze a wallet across all chains: native balances, tokens, fees, and notional POKT relay cost.",
            arguments=[PromptArgument(name="address", description="Wallet address to analyze", required=True)],
        ),
        Prompt(
            name="find_cheapest_chain",
            description="Find the cheapest chain for a given operation type and explain the trade-offs.",
            arguments=[
                PromptArgument(
                    name="operation_type",
                    description="native_transfer | erc20_transfer | contract_call | simulate",
                    required=True,
                )
            ],
        ),
        Prompt(
            name="track_pokt_costs",
            description="Track POKT relay costs over time for an agent and break them down per chain.",
            arguments=[PromptArgument(name="agent_id", description="Agent ID to track", required=True)],
        ),
        Prompt(
            name="compare_and_recommend",
            description="Compare a set of chains and recommend the best one for an operation.",
            arguments=[
                PromptArgument(name="chains", description="Comma-separated chain keys, e.g. ethereum,polygon,arbitrum", required=True),
                PromptArgument(name="operation_type", description="Operation to optimize for (optional)", required=False),
            ],
        ),
    ]


def get_mcp_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Resolve a prompt template to a concrete user message for the client."""
    args = arguments or {}

    def _a(key: str) -> str:
        return args.get(key, "")

    templates: dict[str, str] = {
        "analyze_wallet": (
            f"Analyze the wallet {_a('address')} across all chains I have access to. "
            "Use the analyze_wallet tool to fetch native balances, discovered tokens, "
            "estimated fees, and the notional POKT relay cost for the analysis. "
            "Summarize the portfolio with USD values and call out any chain where the "
            "wallet holds a meaningful balance."
        ),
        "find_cheapest_chain": (
            f"I want to perform a {_a('operation_type')}. Use the recommend_chain tool "
            f"to find the cheapest chain for a {_a('operation_type')}, then use "
            "estimate_transaction_cost on the recommended chain to show the expected "
            "gas + token cost in native units and USD. Explain why this chain was chosen."
        ),
        "track_pokt_costs": (
            f"Track POKT relay costs for agent {_a('agent_id')}. Use get_relay_stats and "
            "get_cost_breakdown to show total relays, notional POKT spent, and the per-chain "
            "breakdown. Frame the POKT figure as a notional estimate (the public Pocket "
            "portal costs users zero POKT) and note how caching has reduced relay consumption."
        ),
        "compare_and_recommend": (
            f"Compare the chains {_a('chains')}. Use compare_chains to show gas prices, "
            "block heights, and health side by side"
            + (f", then use recommend_chain to pick the best for a {_a('operation_type')}." if _a("operation_type") else ", then recommend the best chain overall.")
        ),
    }

    text = templates.get(
        name,
        f"Unknown prompt: {name}. Available prompts: {', '.join(p.name for p in list_mcp_prompts())}.",
    )
    return GetPromptResult(
        description=f"PocketAgent prompt: {name}",
        messages=[
            PromptMessage(role="user", content=TextContent(type="text", text=text)),
        ],
    )
