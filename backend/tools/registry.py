from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal


logger = logging.getLogger(__name__)

Capability = Literal["read", "compare", "transact", "analytics"]
ToolExecutor = Callable[["ToolContext", dict[str, Any]], Awaitable[Any]]


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


def get_tool_schemas(capabilities: set[str]) -> list[dict[str, Any]]:
    return [
        spec.schema
        for spec in TOOL_REGISTRY.values()
        if spec.capability in capabilities or spec.capability == "read" and "read" in capabilities
    ]


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
    allowed_chains = set(context.agent.get("chains") or [])
    if allowed_chains and chain not in allowed_chains:
        raise ValueError(f"Chain '{chain}' is not enabled for this agent.")
    return chain


def validate_chains_allowed(context: ToolContext, chains: list[str]) -> list[str]:
    return [validate_chain_allowed(context, chain) for chain in chains]
