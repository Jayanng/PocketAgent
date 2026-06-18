"""Minimal PocketAgent MCP server bootstrap.

The full tool/resource registration is implemented in the later MCP prompt.
This module keeps the Prompt 2 scaffold importable and gives later work a
stable entry point.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MCPServerConfig:
    name: str = "PocketAgent"
    version: str = "0.1.0"
    description: str = "PocketAgent MCP server for Pocket Network chain data"


@dataclass
class PocketAgentMCPServer:
    config: MCPServerConfig = field(default_factory=MCPServerConfig)

    def startup_info(self) -> dict[str, str]:
        return {
            "name": self.config.name,
            "version": self.config.version,
            "description": self.config.description,
        }


def create_server() -> PocketAgentMCPServer:
    return PocketAgentMCPServer()
