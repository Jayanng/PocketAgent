from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal


logger = logging.getLogger(__name__)

Capability = Literal["read", "compare", "transact", "analytics"]
ToolExecutor = Callable[["ToolContext", dict[str, Any]], Awaitable[Any]]


def is_testnet_chain(chain: str) -> bool:
    """Check if a chain name matches a known testnet.

    PocketAgent is mainnet-only. This function is used to reject testnet
    chain names before they reach any RPC endpoint. It checks:
    - Direct membership in the TESTNET_CHAIN_NAMES set
    - Contains known testnet substrings like "testnet", "devnet"
    - Known testnet chain slugs like "sepolia", "goerli"
    """
    try:
        from ..config import TESTNET_CHAIN_NAMES
    except ImportError:
        from config import TESTNET_CHAIN_NAMES

    normalized = chain.strip().lower().replace("_", "-")
    if normalized in TESTNET_CHAIN_NAMES:
        return True
    # Also catch variants the hard-coded set might miss.
    for keyword in ("testnet", "devnet", "betanet"):
        if keyword in normalized:
            return True
    return False


@dataclass
class ToolContext:
    agent: dict[str, Any]
    rpc_client: Any
    relay_tracker: Any
    db: Any | None = None
    conversation_id: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    schema: dict[str, Any]
    capability: Capability
    executor: ToolExecutor

    @property
    def name(self) -> str:
        return str(self.schema["function"]["name"])


TOOL_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(schema: dict[str, Any], capability: Capability, executor: ToolExecutor) -> ToolSpec:
    spec = ToolSpec(schema=schema, capability=capability, executor=executor)
    TOOL_REGISTRY[spec.name] = spec
    return spec


def function_schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


_PROTOCOL_PREFIXES: dict[str, tuple[str, ...]] = {
    "evm": ("evm_",),
    "solana": ("solana_",),
    "cosmos": ("cosmos_",),
    "sui": ("sui_",),
    "near": ("near_",),
    "tron": ("tron_",),
}

_PROTOCOL_NAMED_TOOLS: dict[str, str] = {
    "send_erc20": "evm",
    "send_spl_token": "solana",
    "send_ibc_token": "cosmos",
    "send_cw20_token": "cosmos",
    "send_sui_token": "sui",
    "send_nep141_token": "near",
    "send_trc20_token": "tron",
}


def _tool_protocols(tool_name: str) -> set[str] | None:
    """Protocols a tool exclusively targets. ``None`` = cross-protocol / always eligible."""
    for protocol, prefixes in _PROTOCOL_PREFIXES.items():
        if any(tool_name.startswith(prefix) for prefix in prefixes):
            return {protocol}
    mapped = _PROTOCOL_NAMED_TOOLS.get(tool_name)
    return {mapped} if mapped else None


def _agent_protocols(agent_chains: list[str] | None) -> set[str] | None:
    if not agent_chains:
        return None
    try:
        from ..services.chain_registry import canonical_chain, get_chain_metadata
    except ImportError:
        from services.chain_registry import canonical_chain, get_chain_metadata

    protocols: set[str] = set()
    for chain in agent_chains:
        try:
            protocols.add(get_chain_metadata(canonical_chain(chain))["protocol"])
        except KeyError:
            continue
    return protocols or None


def get_tool_schemas(
    capabilities: set[str],
    agent_chains: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return OpenAI tool schemas for an agent.

    When ``agent_chains`` is provided, protocol-specific tools that do not
    match any enabled chain family are omitted. This shrinks the prompt sent
    to the LLM on every chat turn — a major TTFT win on Fly where a 70B
    model must ingest 30–40 tool definitions before the first token.
    """
    allowed_protocols = _agent_protocols(agent_chains)
    schemas: list[dict[str, Any]] = []
    for spec in TOOL_REGISTRY.values():
        if not (
            spec.capability in capabilities
            or spec.capability == "read"
            and "read" in capabilities
        ):
            continue
        if allowed_protocols is not None:
            required = _tool_protocols(spec.name)
            if required is not None and required.isdisjoint(allowed_protocols):
                continue
        schemas.append(spec.schema)
    return schemas


async def execute_tool(name: str, context: ToolContext, args: dict[str, Any]) -> Any:
    try:
        spec = TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported tool: {name}") from exc
    try:
        return await spec.executor(context, args)
    except PermissionError:
        # Control-flow signal from the spending-cap / permission guards — keep
        # propagating so callers (and the cap-enforcement tests) still see it.
        raise
    except Exception as exc:  # noqa: BLE001 - operational failures must not abort the turn
        # An upstream Pocket RPC endpoint failed (e.g. 500/408 after retries) or
        # a tool raised on a dead/unreachable chain. Returning a structured
        # "unavailable" result lets the LLM/MCP client react gracefully instead
        # of crashing the whole agent turn (chat HTTP 503).
        logger.warning("Tool '%s' failed; returning unavailable result: %s", name, exc)
        return _unavailable_result(name, args, exc)


def _unavailable_result(name: str, args: dict[str, Any], exc: Exception) -> dict[str, Any]:
    """Structured result for a tool whose RPC call failed. Mirrors the shape
    already used by ``radix_unavailable`` so callers get a consistent signal."""
    result: dict[str, Any] = {
        "available": False,
        "error": f"{type(exc).__name__}: {exc}",
        "tool": name,
    }
    if isinstance(args, dict) and args.get("chain"):
        result["chain"] = args["chain"]
    return result


def validate_chain_allowed(context: ToolContext, chain: str) -> str:
    if is_testnet_chain(chain):
        raise ValueError(
            f"PocketAgent only supports mainnet chains. "
            f"'{chain}' is a testnet network. "
            "If you want to check a mainnet balance, use the mainnet chain name "
            "(e.g. 'ethereum' instead of 'sepolia')."
        )
    allowed_chains = set(context.agent.get("chains") or [])
    if allowed_chains and chain not in allowed_chains:
        raise ValueError(f"Chain '{chain}' is not enabled for this agent.")
    return chain


def validate_chains_allowed(context: ToolContext, chains: list[str]) -> list[str]:
    return [validate_chain_allowed(context, chain) for chain in chains]
