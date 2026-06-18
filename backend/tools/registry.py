from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal


Capability = Literal["read", "compare", "transact", "analytics"]
ToolExecutor = Callable[["ToolContext", dict[str, Any]], Awaitable[Any]]


@dataclass
class ToolContext:
    agent: dict[str, Any]
    rpc_client: Any
    relay_tracker: Any
    db: Any | None = None


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
    return await spec.executor(context, args)


def validate_chain_allowed(context: ToolContext, chain: str) -> str:
    allowed_chains = set(context.agent.get("chains") or [])
    if allowed_chains and chain not in allowed_chains:
        raise ValueError(f"Chain '{chain}' is not enabled for this agent.")
    return chain


def validate_chains_allowed(context: ToolContext, chains: list[str]) -> list[str]:
    return [validate_chain_allowed(context, chain) for chain in chains]
