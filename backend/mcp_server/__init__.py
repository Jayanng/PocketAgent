"""PocketAgent MCP server package.

Exposes the 49 PocketAgent tools, 5 resources, and 4 prompts over MCP stdio.
The server is a thin adapter over backend/tools/TOOL_REGISTRY — `call_tool`
delegates to `execute_tool`, the same path the chat UI uses.

Run with:
    python -m backend.mcp_server.server
"""

from __future__ import annotations

from .prompts import get_mcp_prompt, list_mcp_prompts
from .resources import list_mcp_resources, read_resource_contents
from .server import main, server
from .tools import list_mcp_tools, mcp_tool_names

__all__ = [
    "get_mcp_prompt",
    "list_mcp_prompts",
    "list_mcp_resources",
    "list_mcp_tools",
    "main",
    "mcp_tool_names",
    "read_resource_contents",
    "server",
]
