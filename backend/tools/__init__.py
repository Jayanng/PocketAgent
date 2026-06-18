"""Tool registry for OpenAI function calling."""

from __future__ import annotations

from .registry import TOOL_REGISTRY, ToolContext, execute_tool, get_tool_schemas

# Import modules for registration side effects.
from . import analytics_tools as analytics_tools
from . import balance_tools as balance_tools
from . import chain_tools as chain_tools
from . import compare_tools as compare_tools
from . import pokt_tools as pokt_tools
from . import simulation_tools as simulation_tools
from . import token_tools as token_tools
from . import transaction_tools as transaction_tools
from . import wallet_tools as wallet_tools

ALL_TOOL_DEFINITIONS = [spec.schema for spec in TOOL_REGISTRY.values()]

__all__ = [
    "ALL_TOOL_DEFINITIONS",
    "TOOL_REGISTRY",
    "ToolContext",
    "execute_tool",
    "get_tool_schemas",
]
