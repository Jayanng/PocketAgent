"""MCP Resources — expose chain metadata, chain status, agent stats, agent
wallet, and cache stats as addressable resources.

Resources are read-only context an MCP client can pull (unlike tools, which
act). BlockchainQuery has no resources — these are a PocketAgent addition.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

import aiosqlite
from mcp.types import AnyUrl, Resource


@dataclass
class ReadResourceContents:
    """Minimal resource-content envelope.

    The installed mcp version's read_resource wrapper duck-types
    `content_item.content` + `content_item.mime_type` (the canonical
    ReadResourceContents type isn't exported in this version), so we provide
    a tiny structural stand-in. `content` carries the JSON text.
    """

    content: str
    mime_type: str | None = "application/json"


try:
    from ..config import ensure_database_directory
    from ..database import get_agent
    from ..services.agent_auth import verify_agent_access_token
    from ..services.chain_registry import CHAIN_REGISTRY
    from ..services.pocket_rpc import PocketRPCClient
    from ..services.relay_tracker import RelayTrackerService
except ImportError:
    from config import ensure_database_directory
    from database import get_agent
    from services.agent_auth import verify_agent_access_token
    from services.chain_registry import CHAIN_REGISTRY
    from services.pocket_rpc import PocketRPCClient
    from services.relay_tracker import RelayTrackerService


def list_mcp_resources() -> list[Resource]:
    """Static resource list. Templated URIs (containing {placeholders}) are
    documented here for client discovery; concrete reads resolve them."""
    return [
        Resource(
            uri=AnyUrl("pocket://chains"),
            name="Supported Chains",
            description="All chains with metadata (name, protocol, symbol, RPC URL, explorer)",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("pocket://chains/{chain}/status"),
            name="Chain Status",
            description="Real-time chain health: latest block + latency, probed via Pocket RPC",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("pocket://agents/{agent_id}/stats"),
            name="Agent Stats",
            description="Agent relay statistics. Requires ?agent_access_token=<token>.",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("pocket://agents/{agent_id}/wallet"),
            name="Agent Wallet",
            description="Agent wallet context. Requires ?agent_access_token=<token>.",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("pocket://cache/stats"),
            name="Cache Stats",
            description="Response cache hit/miss counts and estimated POKT relays saved",
            mimeType="application/json",
        ),
    ]


def _default_rpc() -> PocketRPCClient:
    return PocketRPCClient()


def _default_tracker() -> RelayTrackerService:
    return RelayTrackerService()


async def read_resource_contents(
    uri: str,
    *,
    rpc: PocketRPCClient | None = None,
    tracker: RelayTrackerService | None = None,
) -> list[ReadResourceContents]:
    """Resolve a pocket:// URI to JSON text content.

    Accepted URIs:
      pocket://chains
      pocket://chains/{chain}/status
      pocket://agents/{agent_id}/stats?agent_access_token=<token>
      pocket://agents/{agent_id}/wallet?agent_access_token=<token>
      pocket://cache/stats

    Injecting rpc/tracker makes this trivially testable without touching the
    network. The server calls with the defaults.
    """
    rpc = rpc or _default_rpc()
    tracker = tracker or _default_tracker()
    parsed_uri = urlsplit(uri)
    base_uri = uri.split("?", 1)[0]
    query = parse_qs(parsed_uri.query)
    agent_access_token = (query.get("agent_access_token") or [None])[0]

    if base_uri == "pocket://chains":
        payload: dict[str, Any] = {
            chain: {
                "name": meta["name"],
                "protocol": meta["protocol"],
                "symbol": meta["symbol"],
                "url": meta["url"],
                "explorer_url": meta["explorer_url"],
                "chain_id": meta["chain_id"],
            }
            for chain, meta in CHAIN_REGISTRY.items()
        }
        return [_text(json.dumps(payload, indent=2))]

    if base_uri.startswith("pocket://chains/") and base_uri.endswith("/status"):
        chain = base_uri[len("pocket://chains/") : -len("/status")]
        meta = CHAIN_REGISTRY.get(chain)
        if not meta:
            return [_text(json.dumps({"error": f"unknown chain: {chain}"}, indent=2))]
        try:
            block = await rpc.get_block_number(chain)
            status = {"chain": chain, "name": meta["name"], "block_height": block, "status": "live"}
        except Exception as exc:  # surface any probe failure, don't crash the client
            status = {"chain": chain, "name": meta["name"], "status": "unreachable", "error": str(exc)}
        return [_text(json.dumps(status, indent=2))]

    if base_uri.startswith("pocket://agents/") and base_uri.endswith("/stats"):
        agent_id = base_uri[len("pocket://agents/") : -len("/stats")]
        error = await _authorize_agent_resource(agent_id, agent_access_token, rpc)
        if error:
            return [_text(json.dumps({"error": error}, indent=2))]
        stats = await tracker.get_relay_stats(agent_id=agent_id, timeframe="all")
        return [_text(json.dumps(stats, indent=2))]

    if base_uri.startswith("pocket://agents/") and base_uri.endswith("/wallet"):
        agent_id = base_uri[len("pocket://agents/") : -len("/wallet")]
        error = await _authorize_agent_resource(agent_id, agent_access_token, rpc)
        if error:
            return [_text(json.dumps({"error": error}, indent=2))]
        # This resource intentionally avoids exposing private key material. A
        # full balance read is better served by the analyze_wallet tool.
        stats = await tracker.get_relay_stats(agent_id=agent_id, timeframe="all")
        return [_text(json.dumps({"agent_id": agent_id, "relay_summary": stats}, indent=2))]

    if base_uri == "pocket://cache/stats":
        cache_stats = rpc.cache.get_cache_stats()
        return [_text(json.dumps(cache_stats, indent=2))]

    return [_text(json.dumps({"error": f"unsupported resource uri: {uri}"}, indent=2))]


async def _authorize_agent_resource(
    agent_id: str,
    access_token: str | None,
    rpc: PocketRPCClient,
) -> str | None:
    if not access_token:
        return "Valid agent_access_token query parameter is required for this agent resource."

    settings = getattr(rpc, "settings", None)
    database_path = getattr(settings, "database_path", "")
    if not database_path:
        return "Agent database is unavailable for this resource."

    ensure_database_directory(database_path)
    db = await aiosqlite.connect(database_path)
    db.row_factory = aiosqlite.Row
    try:
        agent = await get_agent(db, agent_id)
    finally:
        await db.close()

    if agent is None:
        return f"Agent not found: {agent_id}"
    if not agent.get("is_active", True):
        return f"Agent is inactive: {agent_id}"
    if not verify_agent_access_token(agent, access_token):
        return "Valid agent_access_token query parameter is required for this agent resource."
    return None


def _text(body: str) -> ReadResourceContents:
    return ReadResourceContents(content=body, mime_type="application/json")
