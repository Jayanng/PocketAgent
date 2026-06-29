"""MCP tool surface — converts the existing TOOL_REGISTRY into MCP Tool objects.

The 44 tools (32 read reimplemented from BlockchainQuery's surface + 12 custom)
are already implemented and registered in backend/tools/ with executors. The
MCP server does NOT re-route them; it exposes the same registry as MCP Tool
objects so any MCP client (Claude Desktop, Codex) sees the same surface the
chat path uses. Zero routing drift.

Schema conversion: OpenAI function-call format
  { "type": "function", "function": { "name", "description", "parameters": {...} } }
→ MCP Tool:
  Tool(name=..., description=..., inputSchema={...})
"""

from __future__ import annotations

import copy
from typing import Any

from mcp.types import Tool

try:
    from ..tools import TOOL_REGISTRY
except ImportError:
    from tools import TOOL_REGISTRY


AGENT_ACCESS_TOKEN_PROPERTY = {
    "type": "string",
    "description": "Access token returned when the agent was created.",
}


def _openai_schema_to_input_schema(parameters: dict[str, Any]) -> dict[str, Any]:
    """OpenAI `parameters` and MCP `inputSchema` are both JSON-Schema objects.

    They share the {type, properties, required} shape, so we pass the
    parameters object through. We strip a leading `$schema` key if present
    (some generators add it; MCP clients don't expect it).
    """
    cleaned = {k: v for k, v in copy.deepcopy(parameters).items() if k != "$schema"}
    # MCP requires inputSchema to be an object schema; ensure the type is set.
    cleaned.setdefault("type", "object")
    return cleaned


def _mcp_input_schema(spec: Any) -> dict[str, Any]:
    fn = spec.schema["function"]
    schema = _openai_schema_to_input_schema(fn.get("parameters", {}))
    required = list(schema.get("required", []))
    agent_scoped = "agent_id" in required
    if spec.capability == "transact":
        properties = schema.setdefault("properties", {})
        properties.setdefault("agent_id", {
            "type": "string",
            "description": "Agent ID whose wallet should authorize this transaction.",
        })
        agent_scoped = True
        if "agent_id" not in required:
            required.append("agent_id")
    if agent_scoped:
        properties = schema.setdefault("properties", {})
        properties.setdefault("agent_access_token", AGENT_ACCESS_TOKEN_PROPERTY)
        if "agent_access_token" not in required:
            required.append("agent_access_token")
        schema["required"] = required
    return schema


def list_mcp_tools() -> list[Tool]:
    """Return all 44 registered tools as MCP Tool objects, sorted by name."""
    tools: list[Tool] = []
    for name in sorted(TOOL_REGISTRY):
        spec = TOOL_REGISTRY[name]
        fn = spec.schema["function"]
        tools.append(
            Tool(
                name=fn["name"],
                description=fn.get("description", ""),
                inputSchema=_mcp_input_schema(spec),
            )
        )
    return tools


def mcp_tool_names() -> list[str]:
    """Sorted list of the 44 exposed MCP tool names (handy for docs/tests)."""
    return [t.name for t in list_mcp_tools()]
