"""MCP tool surface — converts the existing TOOL_REGISTRY into MCP Tool objects.

The 49 tools (37 read reimplemented from BlockchainQuery's surface + 12 custom)
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

from typing import Any

from mcp.types import Tool

try:
    from ..tools import TOOL_REGISTRY
except ImportError:
    from tools import TOOL_REGISTRY


def _openai_schema_to_input_schema(parameters: dict[str, Any]) -> dict[str, Any]:
    """OpenAI `parameters` and MCP `inputSchema` are both JSON-Schema objects.

    They share the {type, properties, required} shape, so we pass the
    parameters object through. We strip a leading `$schema` key if present
    (some generators add it; MCP clients don't expect it).
    """
    cleaned = {k: v for k, v in parameters.items() if k != "$schema"}
    # MCP requires inputSchema to be an object schema; ensure the type is set.
    cleaned.setdefault("type", "object")
    return cleaned


def list_mcp_tools() -> list[Tool]:
    """Return all 49 registered tools as MCP Tool objects, sorted by name."""
    tools: list[Tool] = []
    for name in sorted(TOOL_REGISTRY):
        spec = TOOL_REGISTRY[name]
        fn = spec.schema["function"]
        tools.append(
            Tool(
                name=fn["name"],
                description=fn.get("description", ""),
                inputSchema=_openai_schema_to_input_schema(fn.get("parameters", {})),
            )
        )
    return tools


def mcp_tool_names() -> list[str]:
    """Sorted list of the 49 exposed MCP tool names (handy for docs/tests)."""
    return [t.name for t in list_mcp_tools()]
