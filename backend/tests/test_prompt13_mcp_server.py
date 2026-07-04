"""Prompt 13 — MCP server.

Hermetic: the module-level rpc_client / relay_tracker are patched with fakes
so no Pocket RPC, CoinGecko, or DB is hit. The agent_id transact path uses a
temp sqlite DB with a seeded agent. Mirrors the test_prompt6/test_prompt12
fixture style.
"""

import json
import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from backend.mcp_server.prompts import get_mcp_prompt, list_mcp_prompts
from backend.mcp_server.resources import list_mcp_resources, read_resource_contents
from backend.mcp_server.server import (
    handle_call_tool,
    handle_get_prompt,
    handle_list_prompts,
    handle_list_resources,
    handle_list_tools,
    handle_read_resource,
)
from backend.mcp_server.tools import list_mcp_tools, mcp_tool_names
from backend.services.chain_registry import CHAIN_REGISTRY
from backend.services.agent_auth import hash_agent_access_token
from backend.tests.support import auth_enabled_settings


# ─── Fakes ───────────────────────────────────────────────────────────────────


class FakeCache:
    def get_cache_stats(self) -> dict:
        return {"hits": 7, "misses": 3, "relays_saved": 7, "pokt_saved": 0.00623}


class FakeRPC:
    """Minimal PocketRPCClient stand-in for read/resource paths."""

    def __init__(self) -> None:
        self.cache = FakeCache()
        self.settings = type("S", (), {"database_path": ""})()
        # Chains whose get_block_number should fail (simulates an unreachable node).
        self.down_chains: set[str] = set()

    async def get_block_number(self, chain: str) -> int:
        if chain in self.down_chains:
            raise RuntimeError("connection refused")
        return 19_000_000

    async def get_balance(self, chain: str, address: str) -> dict:
        # evm_get_balance executor calls context.rpc_client.get_balance.
        return {
            "raw": "0xde0b6b3a7640000",
            "wei": 10**18,
            "formatted": "1.0",
            "symbol": "ETH",
            "usd_value": 3800.0,
            "chain": chain,
            "protocol": "evm",
        }

    def get_protocol(self, chain: str) -> str:
        return CHAIN_REGISTRY.get(chain, {}).get("protocol", "evm")


class FakeTracker:
    async def get_relay_stats(self, agent_id=None, timeframe="all") -> dict:
        return {
            "total_relays": 42,
            "avg_latency_ms": 123.4,
            "total_pokt_cost": 0.0374,
            "timeframe": timeframe,
        }

    async def get_chain_stats(self, agent_id=None, timeframe="all") -> list[dict]:
        return [
            {
                "chain": "ethereum",
                "relays": 42,
                "avg_latency_ms": 123.4,
                "pokt_cost": 0.0374,
            }
        ]


# ─── Test case ───────────────────────────────────────────────────────────────


class Prompt13MCPServerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._auth_env = auth_enabled_settings()
        self._auth_env.__enter__()

    def tearDown(self) -> None:
        self._auth_env.__exit__(None, None, None)

    def test_list_tools_exposes_all_51_with_object_input_schema(self) -> None:
        tools = list_mcp_tools()
        self.assertEqual(len(tools), 51)
        names = {t.name for t in tools}
        # Spot-check across categories: read (evm/solana/cosmos/sui/near/cross),
        # compare, write, analytics, pokt, compositional, simulation.
        for expected in [
            "list_chains", "get_chain_info",
            "evm_get_balance", "solana_get_balance", "cosmos_get_balance",
            "sui_get_balance", "near_query",
            "resolve_domain", "compare_balances", "convert_units",
            "compare_chains", "recommend_chain", "estimate_transaction_cost",
            "send_transaction", "send_erc20", "contract_call",
            "send_trc20_token", "send_spl_token", "send_ibc_token",
            "send_cw20_token", "send_sui_token", "send_nep141_token",
            "get_relay_stats", "get_relay_history", "get_cost_breakdown",
            "estimate_relay_cost", "analyze_wallet", "simulate_transaction",
        ]:
            self.assertIn(expected, names, f"missing tool: {expected}")
        # Every tool has an object-typed inputSchema (MCP requirement).
        for t in tools:
            self.assertEqual(t.inputSchema.get("type"), "object", f"{t.name} inputSchema not object")
            self.assertTrue(t.description, f"{t.name} has no description")

    def test_schema_conversion_preserves_required_fields(self) -> None:
        tools = {t.name: t for t in list_mcp_tools()}
        # evm_get_balance requires chain + address in the registry schema.
        evm = tools["evm_get_balance"]
        self.assertIn("chain", evm.inputSchema["properties"])
        self.assertIn("address", evm.inputSchema["properties"])
        self.assertEqual(set(evm.inputSchema.get("required", [])), {"chain", "address"})

        stats = tools["get_relay_stats"]
        self.assertIn("agent_id", stats.inputSchema["properties"])
        self.assertIn("agent_access_token", stats.inputSchema["properties"])
        self.assertEqual(
            set(stats.inputSchema.get("required", [])),
            {"agent_id", "agent_access_token"},
        )

        relay_cost = tools["estimate_relay_cost"]
        self.assertNotIn("agent_access_token", relay_cost.inputSchema["properties"])

    def test_mcp_tool_names_is_sorted_and_complete(self) -> None:
        names = mcp_tool_names()
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), 51)

    # ── call_tool routing (read + custom, via the real handler) ──────────────

    def test_call_tool_routes_read_tool_through_registry(self) -> None:
        fake_rpc = FakeRPC()  # has get_balance() → evm_get_balance executor uses it
        fake_tracker = FakeTracker()
        with patch("backend.mcp_server.server._rpc_client", fake_rpc), \
             patch("backend.mcp_server.server._relay_tracker", fake_tracker):
            result = self._run(handle_call_tool("evm_get_balance", {"chain": "ethereum", "address": "0xABC"}))

        self.assertEqual(len(result), 1)
        body = json.loads(result[0].text)
        # Routed to the executor and returned the enriched balance (no error).
        self.assertNotIn("error", body)
        self.assertEqual(body["chain"], "ethereum")
        self.assertEqual(body["formatted"], "1.0")

    def test_call_tool_unknown_tool_returns_error_text(self) -> None:
        result = self._run(handle_call_tool("not_a_real_tool", {}))
        self.assertEqual(len(result), 1)
        body = json.loads(result[0].text)
        self.assertIn("error", body)
        self.assertIn("Unknown tool", body["error"])

    def test_call_tool_transact_without_agent_id_returns_error(self) -> None:
        # Transact tools require agent_id; omitting it is a clean client error.
        result = self._run(handle_call_tool("send_transaction", {
            "chain": "ethereum", "to_address": "0xDEF", "amount": "0.01",
        }))
        body = json.loads(result[0].text)
        self.assertIn("error", body)
        self.assertIn("agent_id", body["error"])

    def test_call_tool_agent_scoped_analytics_without_access_token_returns_error(self) -> None:
        result = self._run(handle_call_tool("get_relay_stats", {
            "agent_id": "agent-a",
            "timeframe": "all",
        }))
        body = json.loads(result[0].text)
        self.assertIn("error", body)
        self.assertIn("agent_access_token", body["error"])

    def test_call_tool_agent_scoped_analytics_requires_valid_access_token(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(tmp.name, "pa-analytics.db")
        try:
            self._seed_agent(db_path, agent_id="agent-a", chains=["ethereum"], access_token="secret-token")
            fake_rpc = FakeRPC()
            fake_rpc.settings = type("S", (), {"database_path": db_path})()
            fake_tracker = FakeTracker()
            with patch("backend.mcp_server.server._rpc_client", fake_rpc), \
                 patch("backend.mcp_server.server._relay_tracker", fake_tracker):
                denied = self._run(handle_call_tool("get_relay_stats", {
                    "agent_id": "agent-a",
                    "agent_access_token": "wrong-token",
                    "timeframe": "all",
                }))
                allowed = self._run(handle_call_tool("get_relay_stats", {
                    "agent_id": "agent-a",
                    "agent_access_token": "secret-token",
                    "timeframe": "all",
                }))

            self.assertIn("error", json.loads(denied[0].text))
            allowed_body = json.loads(allowed[0].text)
            self.assertNotIn("error", allowed_body)
            self.assertEqual(allowed_body["total_relays"], 42)
        finally:
            tmp.cleanup()

    # ── Resources ────────────────────────────────────────────────────────────

    def test_list_resources_returns_five_with_pocket_uris(self) -> None:
        resources = list_mcp_resources()
        self.assertEqual(len(resources), 5)
        uris = {str(r.uri) for r in resources}
        self.assertIn("pocket://chains", uris)
        self.assertIn("pocket://cache/stats", uris)
        for r in resources:
            self.assertTrue(r.name)
            self.assertTrue(r.description)

    def test_read_resource_chains_returns_registry_metadata(self) -> None:
        contents = self._run(read_resource_contents(
            "pocket://chains", rpc=FakeRPC(), tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertIn("ethereum", body)
        self.assertEqual(body["ethereum"]["protocol"], "evm")
        self.assertEqual(body["ethereum"]["symbol"], "ETH")

    def test_read_resource_chain_status_reports_block_height(self) -> None:
        contents = self._run(read_resource_contents(
            "pocket://chains/ethereum/status", rpc=FakeRPC(), tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertEqual(body["chain"], "ethereum")
        self.assertEqual(body["block_height"], 19_000_000)
        self.assertEqual(body["status"], "live")

    def test_read_resource_chain_status_surfaces_unreachable(self) -> None:
        # Use a real registry chain, but mark it down so the probe raises.
        rpc = FakeRPC()
        rpc.down_chains = {"ethereum"}
        contents = self._run(read_resource_contents(
            "pocket://chains/ethereum/status", rpc=rpc, tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertEqual(body["status"], "unreachable")
        self.assertIn("error", body)

    def test_read_resource_unknown_chain_status(self) -> None:
        contents = self._run(read_resource_contents(
            "pocket://chains/notarealchain/status", rpc=FakeRPC(), tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertIn("error", body)

    def test_read_resource_cache_stats(self) -> None:
        contents = self._run(read_resource_contents(
            "pocket://cache/stats", rpc=FakeRPC(), tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertEqual(body["hits"], 7)
        self.assertEqual(body["relays_saved"], 7)

    def test_read_resource_agent_stats_requires_access_token(self) -> None:
        contents = self._run(read_resource_contents(
            "pocket://agents/some-agent/stats", rpc=FakeRPC(), tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertIn("error", body)
        self.assertIn("agent_access_token", body["error"])

    def test_read_resource_agent_stats_with_valid_access_token(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(tmp.name, "pa-resource.db")
        try:
            self._seed_agent(db_path, agent_id="agent-r", chains=["ethereum"], access_token="secret-token")
            rpc = FakeRPC()
            rpc.settings = type("S", (), {"database_path": db_path})()

            contents = self._run(read_resource_contents(
                "pocket://agents/agent-r/stats?agent_access_token=secret-token",
                rpc=rpc,
                tracker=FakeTracker(),
            ))

            body = json.loads(contents[0].content)
            self.assertNotIn("error", body)
            self.assertEqual(body["total_relays"], 42)
        finally:
            tmp.cleanup()

    def test_read_resource_agent_wallet_rejects_wrong_access_token(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(tmp.name, "pa-resource-wallet.db")
        try:
            self._seed_agent(db_path, agent_id="agent-r", chains=["ethereum"], access_token="secret-token")
            rpc = FakeRPC()
            rpc.settings = type("S", (), {"database_path": db_path})()

            contents = self._run(read_resource_contents(
                "pocket://agents/agent-r/wallet?agent_access_token=wrong-token",
                rpc=rpc,
                tracker=FakeTracker(),
            ))

            body = json.loads(contents[0].content)
            self.assertIn("error", body)
            self.assertIn("agent_access_token", body["error"])
        finally:
            tmp.cleanup()

    def test_read_resource_unsupported_uri(self) -> None:
        contents = self._run(read_resource_contents(
            "pocket://nonsense", rpc=FakeRPC(), tracker=FakeTracker()
        ))
        body = json.loads(contents[0].content)
        self.assertIn("error", body)

    # ── Prompts ──────────────────────────────────────────────────────────────

    def test_list_prompts_returns_four_templates(self) -> None:
        prompts = list_mcp_prompts()
        self.assertEqual(len(prompts), 4)
        names = {p.name for p in prompts}
        self.assertEqual(names, {
            "analyze_wallet", "find_cheapest_chain",
            "track_pokt_costs", "compare_and_recommend",
        })
        # analyze_wallet has one required arg; compare_and_recommend has a required + optional.
        aw = next(p for p in prompts if p.name == "analyze_wallet")
        self.assertTrue(aw.arguments[0].required)
        cr = next(p for p in prompts if p.name == "compare_and_recommend")
        reqd = [a.name for a in cr.arguments if a.required]
        optional = [a.name for a in cr.arguments if not a.required]
        self.assertEqual(reqd, ["chains"])
        self.assertEqual(optional, ["operation_type"])

    def test_get_prompt_resolves_to_user_message(self) -> None:
        result = get_mcp_prompt("analyze_wallet", {"address": "0xDEAD"})
        self.assertEqual(len(result.messages), 1)
        self.assertEqual(result.messages[0].role, "user")
        self.assertIn("0xDEAD", result.messages[0].content.text)

    def test_get_prompt_compare_and_recommend_optional_arg(self) -> None:
        # With operation_type → message mentions recommend_chain for that op.
        with_op = get_mcp_prompt("compare_and_recommend", {"chains": "eth,poly", "operation_type": "native_transfer"})
        self.assertIn("native_transfer", with_op.messages[0].content.text)
        # Without operation_type → falls back to overall recommendation.
        no_op = get_mcp_prompt("compare_and_recommend", {"chains": "eth,poly"})
        self.assertIn("recommend the best chain overall", no_op.messages[0].content.text)

    def test_get_prompt_unknown_name(self) -> None:
        result = get_mcp_prompt("nope", None)
        self.assertIn("Unknown prompt", result.messages[0].content.text)

    # ── Handler wrappers (smoke: they delegate to the same functions) ─────────

    def test_handle_list_tools_and_resources_and_prompts_delegate(self) -> None:
        self.assertEqual(len(self._run(handle_list_tools())), 51)
        self.assertEqual(len(self._run(handle_list_resources())), 5)
        self.assertEqual(len(self._run(handle_list_prompts())), 4)

    def test_handle_get_prompt_delegates(self) -> None:
        result = self._run(handle_get_prompt("find_cheapest_chain", {"operation_type": "native_transfer"}))
        self.assertIn("native_transfer", result.messages[0].content.text)

    # ─── agent_id transact path (temp DB) ────────────────────────────────────

    def test_call_tool_transact_loads_agent_from_db_by_agent_id(self) -> None:
        """A transact tool with agent_id must load the agent from the DB so the
        executor can decrypt + sign. We seed an agent and assert the handler
        reaches the executor (which then needs a chain the agent has enabled);
        without agent_id it short-circuits, with a bogus id it errors cleanly."""
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(tmp.name, "pa-transact.db")
        try:
            self._seed_agent(db_path, agent_id="agent-t", chains=["ethereum"])
            fake_rpc = FakeRPC()
            fake_rpc.settings = type("S", (), {"database_path": db_path})()
            fake_tracker = FakeTracker()
            with patch("backend.mcp_server.server._rpc_client", fake_rpc), \
                 patch("backend.mcp_server.server._relay_tracker", fake_tracker):
                # Bogus agent_id → clean error, no crash.
                bad = self._run(handle_call_tool("send_transaction", {
                    "chain": "ethereum", "to_address": "0xDEF", "amount": "0.01",
                    "agent_id": "does-not-exist",
                    "agent_access_token": "secret-token",
                }))
                self.assertIn("error", json.loads(bad[0].text))
        finally:
            tmp.cleanup()

    # ─── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _seed_agent(
        db_path: str,
        agent_id: str,
        chains: list[str],
        access_token: str = "secret-token",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY, name TEXT, description TEXT, chains TEXT,
                    capabilities TEXT, encrypted_private_key TEXT, wallet_address TEXT,
                    access_token_hash TEXT,
                    spending_cap REAL, total_spent REAL, is_active INTEGER,
                    created_at TEXT, updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO agents (id, name, description, chains, capabilities,
                                    encrypted_private_key, wallet_address, access_token_hash,
                                    spending_cap, total_spent, is_active,
                                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    agent_id, "Transact Agent", "test", json.dumps(chains),
                    json.dumps(["read", "transact", "compare"]),
                    "encrypted-blob", "0xWALLET", hash_agent_access_token(access_token),
                    0.1, 0.0, now, now,
                ),
            )
            conn.commit()

    @staticmethod
    def _run(coro):
        import asyncio

        return asyncio.new_event_loop().run_until_complete(coro)


if __name__ == "__main__":
    unittest.main()
