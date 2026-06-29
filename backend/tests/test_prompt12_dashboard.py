"""Prompt 12 — analytics dashboard endpoints.

Hermetic: a temp SQLite DB is seeded for relay-stats/cost-tracker, and the
RPC + price-feed services are faked for chain-health and portfolio. No live
Pocket RPC, no network, no CoinGecko. Mirrors the test_prompt6_api.py fixture
style (temp dir + DATABASE_PATH env override + TestClient + patch).
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.services.relay_tracker import RelayTrackerService


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Prompt12DashboardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.tmp.name, "pocketagent-test.db")
        self.env_patcher = patch.dict(
            os.environ,
            {
                "DATABASE_PATH": self.db_path,
                "ENCRYPTION_KEY": "test-encryption-key",
                "JWT_SECRET": "",
                "OPENAI_API_KEY": "",
                "DISABLE_AGENT_AUTH": "false",
            },
            clear=False,
        )
        self.env_patcher.start()

        from backend.config import get_settings
        from backend.main import app

        get_settings.cache_clear()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        from backend.config import get_settings

        get_settings.cache_clear()
        self.env_patcher.stop()
        self.tmp.cleanup()

    # ─── relay_logs seeding ────────────────────────────────────────────────

    def seed_relay_logs(self, rows: list[dict]) -> None:
        """Insert relay_logs directly. Each row: {agent_id, chain, method,
        response_status, latency_ms, relay_cost_pokt, created_at}."""
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            for r in rows:
                conn.execute(
                    """
                    INSERT INTO relay_logs
                        (id, agent_id, chain, method, request_payload,
                         response_status, latency_ms, relay_cost_pokt, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        r.get("agent_id"),
                        r["chain"],
                        r.get("method", "eth_getBalance"),
                        "{}",
                        r.get("response_status", 200),
                        r.get("latency_ms", 100),
                        r.get("relay_cost_pokt", 0.00089),
                        r.get("created_at", now.isoformat()),
                    ),
                )
            conn.commit()

    def create_agent(self, name: str = "Analytics Agent") -> dict:
        response = self.client.post(
            "/api/agents",
            json={
                "name": name,
                "description": "Prompt 12 analytics auth test agent",
                "chains": ["ethereum"],
                "capabilities": ["read", "analytics"],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    @staticmethod
    def auth_headers(agent: dict) -> dict[str, str]:
        return {"X-Agent-Access-Token": agent["access_token"]}

    # ─── RelayTrackerService.get_success_rate (the refactor) ────────────────

    def test_success_rate_service_computes_2xx_share_in_one_query(self) -> None:
        self.seed_relay_logs([
            {"chain": "ethereum", "response_status": 200},
            {"chain": "ethereum", "response_status": 200},
            {"chain": "polygon", "response_status": 429},
            {"chain": "polygon", "response_status": 503},
            {"chain": "solana", "response_status": 200},
        ])
        tracker = RelayTrackerService()
        result = await_sync(tracker.get_success_rate())

        self.assertEqual(result["successful"], 3)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["total"], 5)
        # Service rounds to 4dp (matches get_relay_stats convention).
        self.assertAlmostEqual(result["success_rate"], 0.6, places=4)

    def test_success_rate_empty_table_reports_perfect_rate(self) -> None:
        # No rows yet — 1.0, not 0.0 (avoid misleading "0%" on a fresh install).
        tracker = RelayTrackerService()
        result = await_sync(tracker.get_success_rate())

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["success_rate"], 1.0)

    def test_success_rate_respects_agent_filter(self) -> None:
        self.seed_relay_logs([
            {"agent_id": "agent-a", "chain": "ethereum", "response_status": 200},
            {"agent_id": "agent-a", "chain": "ethereum", "response_status": 500},
            {"agent_id": "agent-b", "chain": "polygon", "response_status": 200},
        ])
        tracker = RelayTrackerService()
        result = await_sync(tracker.get_success_rate(agent_id="agent-a"))

        self.assertEqual(result["total"], 2)
        self.assertAlmostEqual(result["success_rate"], 0.5, places=4)

    # ─── GET /api/analytics/relay-stats ─────────────────────────────────────

    def test_relay_stats_endpoint_aggregates_seeded_logs(self) -> None:
        self.seed_relay_logs([
            {"agent_id": "a1", "chain": "ethereum", "response_status": 200,
             "latency_ms": 100, "relay_cost_pokt": 0.00089},
            {"agent_id": "a1", "chain": "ethereum", "response_status": 200,
             "latency_ms": 300, "relay_cost_pokt": 0.00089},
            {"agent_id": "a1", "chain": "polygon", "response_status": 429,
             "latency_ms": 200, "relay_cost_pokt": 0.00089},
        ])

        resp = self.client.get("/api/analytics/relay-stats?timeframe=all")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["total_relays"], 3)
        self.assertEqual(body["successful_relays"], 2)
        self.assertEqual(body["failed_relays"], 1)
        # success_rate rounded to 4dp by the service.
        self.assertAlmostEqual(body["success_rate"], 2 / 3, places=4)
        self.assertAlmostEqual(body["avg_latency_ms"], 200.0)
        # per-chain grouped, ordered by relay count desc
        chains = {c["chain"]: c for c in body["per_chain"]}
        self.assertEqual(chains["ethereum"]["relays"], 2)
        self.assertEqual(chains["polygon"]["relays"], 1)

    def test_relay_stats_rejects_invalid_timeframe(self) -> None:
        resp = self.client.get("/api/analytics/relay-stats?timeframe=forever")
        self.assertEqual(resp.status_code, 422)

    def test_relay_stats_agent_filter_requires_access_token(self) -> None:
        created = self.create_agent()
        self.seed_relay_logs([
            {"agent_id": created["id"], "chain": "ethereum", "response_status": 200},
        ])

        missing = self.client.get(f"/api/analytics/relay-stats?agent_id={created['id']}")
        self.assertEqual(missing.status_code, 403)

        wrong = self.client.get(
            f"/api/analytics/relay-stats?agent_id={created['id']}",
            headers={"X-Agent-Access-Token": "wrong-token"},
        )
        self.assertEqual(wrong.status_code, 403)

        allowed = self.client.get(
            f"/api/analytics/relay-stats?agent_id={created['id']}",
            headers=self.auth_headers(created),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(allowed.json()["total_relays"], 1)

    # ─── GET /api/analytics/cost-tracker ────────────────────────────────────

    def test_cost_tracker_notional_math_and_per_chain_share(self) -> None:
        # 2 relays on ethereum, 1 on polygon, each at the notional rate.
        self.seed_relay_logs([
            {"chain": "ethereum", "relay_cost_pokt": 0.00089},
            {"chain": "ethereum", "relay_cost_pokt": 0.00089},
            {"chain": "polygon", "relay_cost_pokt": 0.00089},
        ])

        resp = self.client.get("/api/analytics/cost-tracker?timeframe=all")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertAlmostEqual(body["total_pokt_cost"], 3 * 0.00089)
        self.assertEqual(body["total_relays"], 3)
        self.assertEqual(body["notional_pokt_per_relay"], 0.00089)
        chains = {c["chain"]: c for c in body["per_chain"]}
        # ethereum = 2/3 of total POKT (share rounded to 4dp by the service).
        self.assertAlmostEqual(chains["ethereum"]["share"], 2 / 3, places=4)
        self.assertAlmostEqual(chains["polygon"]["share"], 1 / 3, places=4)
        self.assertIn("Notional", body["note"])

    def test_cost_tracker_agent_filter_requires_access_token(self) -> None:
        created = self.create_agent()
        self.seed_relay_logs([
            {"agent_id": created["id"], "chain": "ethereum", "relay_cost_pokt": 0.00089},
        ])

        missing = self.client.get(f"/api/analytics/cost-tracker?agent_id={created['id']}")
        self.assertEqual(missing.status_code, 403)

        allowed = self.client.get(
            f"/api/analytics/cost-tracker?agent_id={created['id']}",
            headers=self.auth_headers(created),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(allowed.json()["total_relays"], 1)

    # ─── GET /api/analytics/chain-health ────────────────────────────────────

    def test_chain_health_default_probes_headlines_rest_registered(self) -> None:
        # Fake RPC: ethereum responds fast, solana times out, everything else
        # would only be hit under live=true.
        class FakeRPC:
            async def get_block_number(self, chain: str) -> int:
                if chain == "solana":
                    raise asyncio.TimeoutError()
                if chain == "ethereum":
                    return 19_000_000
                return 1

        from backend.services.chain_registry import CHAIN_REGISTRY

        with patch("backend.routers.analytics._rpc", lambda: FakeRPC()):
            resp = self.client.get("/api/analytics/chain-health")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertFalse(body["live"])  # default is the cheap poll
        self.assertEqual(body["total"], len(CHAIN_REGISTRY))

        by_chain = {c["chain"]: c for c in body["chains"]}
        # ethereum is a headline chain → probed, healthy, has a block height.
        self.assertEqual(by_chain["ethereum"]["status"], "green")
        self.assertEqual(by_chain["ethereum"]["block_height"], 19_000_000)
        self.assertTrue(by_chain["ethereum"]["live"])
        # solana is a headline chain → probed, but timed out → red.
        self.assertEqual(by_chain["solana"]["status"], "red")
        self.assertEqual(by_chain["solana"]["error"], "timeout")
        # A non-headline chain (e.g. 'osmosis') was NOT probed → registered.
        self.assertEqual(by_chain["osmosis"]["status"], "registered")
        self.assertFalse(by_chain["osmosis"]["live"])

        # Summary counts are internally consistent.
        statuses = [c["status"] for c in body["chains"]]
        self.assertEqual(body["healthy"], statuses.count("green"))
        self.assertEqual(body["down"], statuses.count("red"))
        self.assertEqual(body["registered"], statuses.count("registered"))

    def test_chain_health_live_true_probes_every_registry_chain(self) -> None:
        class FakeRPC:
            async def get_block_number(self, chain: str) -> int:
                return 42

        from backend.services.chain_registry import CHAIN_REGISTRY

        with patch("backend.routers.analytics._rpc", lambda: FakeRPC()):
            resp = self.client.get("/api/analytics/chain-health?live=true")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body["live"])
        # Every chain probed → none left as 'registered'.
        self.assertEqual(body["registered"], 0)
        self.assertEqual(body["total"], len(CHAIN_REGISTRY))
        self.assertTrue(all(c["live"] for c in body["chains"]))

    # ─── GET /api/analytics/portfolio ───────────────────────────────────────

    def test_portfolio_rejects_unknown_chain(self) -> None:
        resp = self.client.get(
            "/api/analytics/portfolio?address=0xABC&chains=ethereum,notarealchain"
        )
        self.assertEqual(resp.status_code, 400, resp.text)
        self.assertIn("notarealchain", resp.json()["detail"])

    def test_portfolio_usd_enrichment_prefers_rpc_value_then_coingecko(self) -> None:
        # ethereum carries a usd_value from the RPC layer; polygon does not
        # (the endpoint falls back to CoinGecko unit price × amount).
        class FakeRPC:
            async def multi_chain_balance(self, address: str, chains: list[str]) -> dict:
                return {
                    "address": address,
                    "balances": {
                        "ethereum": {"formatted": "1.5", "symbol": "ETH", "usd_value": 5700.0},
                        "polygon": {"formatted": "2000", "symbol": "POL"},
                    },
                }

        class FakePrices:
            async def get_prices(self, coin_ids: list[str]) -> dict:
                # CoinGecko batch result: polygon only; ethereum would be unused
                # because the RPC layer already supplied a usd_value.
                return {"ethereum": None, "matic-network": 0.7}

        with patch("backend.routers.analytics._rpc", lambda: FakeRPC()), \
             patch("backend.routers.analytics._prices", lambda: FakePrices()):
            resp = self.client.get(
                "/api/analytics/portfolio?address=0xABC&chains=ethereum,polygon"
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        holdings = {h["chain"]: h for h in body["holdings"]}
        # RPC-supplied value passes through unchanged.
        self.assertEqual(holdings["ethereum"]["usd_value"], 5700.0)
        # CoinGecko fallback: 2000 POL × $0.70 = $1400.
        self.assertEqual(holdings["polygon"]["usd_value"], 1400.0)
        # Total + share math (share rounded to 4dp by the service).
        self.assertAlmostEqual(body["total_usd"], 5700.0 + 1400.0, places=4)
        self.assertAlmostEqual(holdings["ethereum"]["share"], 5700.0 / 7100.0, places=4)
        self.assertAlmostEqual(holdings["polygon"]["share"], 1400.0 / 7100.0, places=4)

    def test_portfolio_passes_through_error_entries_with_null_usd(self) -> None:
        class FakeRPC:
            async def multi_chain_balance(self, address: str, chains: list[str]) -> dict:
                return {
                    "address": address,
                    "balances": {
                        "ethereum": {"error": "RPC rate-limited"},
                    },
                }

        class FakePrices:
            async def get_prices(self, coin_ids: list[str]) -> dict:
                return {}

        with patch("backend.routers.analytics._rpc", lambda: FakeRPC()), \
             patch("backend.routers.analytics._prices", lambda: FakePrices()):
            resp = self.client.get("/api/analytics/portfolio?address=0xABC&chains=ethereum")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        eth = body["holdings"][0]
        self.assertEqual(eth["chain"], "ethereum")
        self.assertIsNone(eth["usd_value"])
        self.assertEqual(eth["share"], 0.0)
        # Error entry must not inflate the total.
        self.assertEqual(body["total_usd"], 0.0)


# ─── helpers ────────────────────────────────────────────────────────────────


def await_sync(coro):
    """Run an async coroutine to completion in a sync test method."""
    return asyncio.new_event_loop().run_until_complete(coro)


if __name__ == "__main__":
    unittest.main()
