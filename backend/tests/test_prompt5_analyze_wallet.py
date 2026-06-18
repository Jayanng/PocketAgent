import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.tools.registry import ToolContext
from backend.tools.wallet_tools import analyze_wallet


class _FakeRPCClient:
    """Deterministic, offline stand-in for PocketRPCClient covering the
    methods analyze_wallet orchestrates: native balances, token discovery,
    gas/fee estimate, protocol lookup, and settings."""

    def __init__(self) -> None:
        self.settings = SimpleNamespace(notional_pokt_per_relay=0.00089)

    def get_protocol(self, chain: str) -> str:
        return {"ethereum": "evm", "solana": "solana", "osmosis": "cosmos"}[chain]

    async def multi_chain_balance(self, address: str, chains: list[str]) -> dict:
        return {
            "address": address,
            "balances": {
                "ethereum": {"formatted": "1.5 ETH", "symbol": "ETH", "usd_value": 4500.0, "amount_decimal": 1.5},
                "solana": {"formatted": "10 SOL", "symbol": "SOL", "usd_value": 1500.0, "amount_decimal": 10.0},
                "osmosis": {"formatted": "100 OSMO", "symbol": "OSMO", "usd_value": 50.0, "amount_decimal": 100.0},
            },
        }

    async def discover_tokens(self, chain: str, address: str) -> list[dict]:
        tokens = {
            "ethereum": [
                {"symbol": "USDC", "contract": "0xa0b8...", "balance_formatted": "2000 USDC", "amount_decimal": 2000.0, "usd_value": 2000.0},
                {"symbol": "LINK", "contract": "0x5149...", "balance_formatted": "50 LINK", "amount_decimal": 50.0, "usd_value": 750.0},
            ],
            "solana": [
                {"symbol": "USDC", "contract": "EPjFWd...", "balance_formatted": "500 USDC", "amount_decimal": 500.0, "usd_value": 500.0},
            ],
            "osmosis": [],  # no extra denoms beyond native
        }
        return tokens.get(chain, [])

    async def get_gas_price(self, chain: str) -> dict:
        return {
            "ethereum": {"chain": "ethereum", "protocol": "evm", "gas_price_gwei": 12.0, "estimated_cost": {"transfer_usd": "$0.30"}},
            "solana": {"chain": "solana", "protocol": "solana", "estimated_native_fee": 0.000005, "estimated_cost": {"transfer_usd": "$0.00"}},
            "osmosis": {"chain": "osmosis", "protocol": "cosmos", "estimated_native_fee": 0.000625, "estimated_cost": {"transfer_usd": "$0.00"}},
        }[chain]


class AnalyzeWalletExpansionTestCase(unittest.IsolatedAsyncioTestCase):
    """Prompt 5 analyze_wallet must be a compositional tool: native balances +
    token discovery + gas/fee estimate + USD-weighted portfolio allocation."""

    def _context(self) -> ToolContext:
        return ToolContext(
            agent={"id": "agent-1", "chains": ["ethereum", "solana", "osmosis"]},
            rpc_client=_FakeRPCClient(),
            relay_tracker=None,
            db=None,
        )

    async def test_includes_token_discovery_per_chain(self) -> None:
        result = await analyze_wallet(self._context(), {"address": "0xabc"})

        self.assertIn("tokens", result)
        self.assertEqual(len(result["tokens"]["ethereum"]), 2)
        self.assertEqual(result["tokens"]["ethereum"][0]["symbol"], "USDC")
        self.assertEqual(len(result["tokens"]["solana"]), 1)
        self.assertEqual(result["tokens"]["osmosis"], [])

    async def test_includes_gas_estimate_per_chain(self) -> None:
        result = await analyze_wallet(self._context(), {"address": "0xabc"})

        self.assertIn("gas_estimate", result)
        self.assertEqual(result["gas_estimate"]["ethereum"]["gas_price_gwei"], 12.0)
        self.assertIn("estimated_native_fee", result["gas_estimate"]["solana"])

    async def test_portfolio_allocation_is_usd_weighted(self) -> None:
        result = await analyze_wallet(self._context(), {"address": "0xabc"})

        portfolio = result["portfolio"]
        # native: 4500 + 1500 + 50 = 6050; tokens: 2000 + 750 + 500 = 3250; total = 9300
        self.assertAlmostEqual(portfolio["total_usd"], 9300.0, places=2)
        allocation_by_asset = {a["asset"]: a for a in portfolio["allocation"]}
        # ETH native 4500 -> 48.39%
        self.assertAlmostEqual(allocation_by_asset["ETH"]["usd"], 4500.0, places=2)
        self.assertAlmostEqual(allocation_by_asset["ETH"]["percentage"], 48.387, places=2)
        # USDC aggregates across chains: 2000 + 500 = 2500 -> 26.88%
        self.assertAlmostEqual(allocation_by_asset["USDC"]["usd"], 2500.0, places=2)
        self.assertAlmostEqual(allocation_by_asset["USDC"]["percentage"], 26.882, places=2)

    async def test_include_tokens_false_omits_token_discovery(self) -> None:
        result = await analyze_wallet(
            self._context(), {"address": "0xabc", "include_tokens": False}
        )
        self.assertNotIn("tokens", result)
        # portfolio still computed from native balances
        self.assertAlmostEqual(result["portfolio"]["total_usd"], 6050.0, places=2)

    async def test_backward_compatible_notional_relay_cost_present(self) -> None:
        result = await analyze_wallet(self._context(), {"address": "0xabc"})
        self.assertIn("notional_relay_cost", result)


if __name__ == "__main__":
    unittest.main()
